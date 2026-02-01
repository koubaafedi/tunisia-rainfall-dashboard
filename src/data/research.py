import pandas as pd
import requests
import streamlit as st
import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from .. import config
from .fetchers import fetch_raw_metadata, fetch_latest_readings_raw

logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_rainfall_metadata() -> pd.DataFrame:
    """Fetches all rainfall monitoring stations in the UK."""
    url = "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall&_limit=5000"
    try:
        resp = requests.get(url, timeout=25)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            df = pd.DataFrame(items)
            res = pd.DataFrame()
            res['rain_station_ref'] = df.get('stationReference')
            res['rain_latitude'] = pd.to_numeric(df.get('lat'), errors='coerce')
            res['rain_longitude'] = pd.to_numeric(df.get('long'), errors='coerce')
            res['rain_label'] = df.get('label', 'Unknown Rain Gauge')
            return res.dropna(subset=['rain_latitude', 'rain_longitude'])
    except Exception as e:
        logger.error(f"Rainfall Meta Fetch Failed: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def link_stations_geospatially(gw_df: pd.DataFrame, max_dist_km: float = 15.0) -> pd.DataFrame:
    """Links each groundwater station to the nearest rainfall gauge."""
    rain_df = fetch_rainfall_metadata()
    if gw_df.empty or rain_df.empty:
        return gw_df

    links = []
    for _, gw in gw_df.iterrows():
        min_dist = float('inf')
        best_match = None
        for _, rain in rain_df.iterrows():
            dist = haversine(gw['latitude'], gw['longitude'], rain['rain_latitude'], rain['rain_longitude'])
            if dist < min_dist:
                min_dist = dist
                best_match = rain

        if best_match is not None and min_dist <= max_dist_km:
            links.append({
                'stationReference': gw['stationReference'],
                'rain_ref': best_match['rain_station_ref'],
                'rain_label': best_match['rain_label'],
                'rain_dist_km': min_dist
            })
    
    link_df = pd.DataFrame(links)
    if link_df.empty: return gw_df
    return pd.merge(gw_df, link_df, on='stationReference', how='left')

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_READINGS)
def fetch_rainfall_readings(rain_refs: List[str], window_days: int) -> pd.DataFrame:
    """Fetches rainfall totals using a high-coverage threaded strategy."""
    if not rain_refs: return pd.DataFrame()
    target_refs = list(set(str(r) for r in rain_refs if r))
    hist_date = (datetime.utcnow() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    try:
        # 1. Map stationRefs to Measure URLs (Batch metadata - Reliable)
        url_m = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=rainfall&_limit=10000"
        resp = requests.get(url_m, timeout=25)
        if resp.status_code != 200: return pd.DataFrame()
        
        items = resp.json().get('items', [])
        ref_to_measure = {}
        for it in items:
            ref = it.get('stationReference') or (it['station'].split('/')[-1] if 'station' in it else None)
            if ref and str(ref) in target_refs:
                ref_to_measure[str(ref)] = it.get('@id')
        
        # 2. Threaded Fetch for Latest AND Historical readings
        def _fetch_pair(ref):
            m_url = ref_to_measure.get(ref)
            if not m_url: return None
            res = {'rain_ref': ref}
            try:
                # Latest
                rl = requests.get(f"{m_url}/readings?latest", timeout=8)
                if rl.status_code == 200:
                    l_items = rl.json().get('items', [])
                    if l_items: res['rain_latest_val'] = float(l_items[0]['value'])
                # History
                rh = requests.get(f"{m_url}/readings?date={hist_date}&_limit=1", timeout=8)
                if rh.status_code == 200:
                    h_items = rh.json().get('items', [])
                    if h_items: res['rain_hist_val'] = float(h_items[0]['value'])
            except: pass
            return res if 'rain_latest_val' in res else None

        with ThreadPoolExecutor(max_workers=25) as executor:
            combined_results = list(executor.map(_fetch_pair, list(ref_to_measure.keys())))
        
        results = [r for r in combined_results if r]
        if results:
            final = pd.DataFrame(results)
            logger.warning(f"Rainfall Pipeline: Coverage {len(final)}/{len(target_refs)} gauges. Hist hits: {final.get('rain_hist_val', pd.Series()).notna().sum()}")
            return final
            
    except Exception as e:
        logger.error(f"Rainfall Pipeline Critical Error: {e}")
        
    return pd.DataFrame()

def fetch_research_data(gw_df: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """Orchestrates the linking and proxy calculation for the research hub."""
    if gw_df.empty: return gw_df
    res = gw_df.copy()
    res['rain_ref'] = None
    res['rain_label'] = "No Gauge Linked"
    res['rain_dist_km'] = 0.0
    res['proxy_trend'] = "N/A"
    res['proxy_match'] = "N/A"
    
    try:
        linked = link_stations_geospatially(gw_df)
        if 'rain_ref' not in linked.columns: return res
        active_rain_refs = linked['rain_ref'].dropna().unique().tolist()
        if not active_rain_refs: return linked.assign(proxy_trend="N/A", proxy_match="N/A")
            
        rain_readings = fetch_rainfall_readings(active_rain_refs, window_days)
        if rain_readings.empty: return linked.assign(proxy_trend="N/A", proxy_match="N/A")
        
        res = pd.merge(linked, rain_readings, on='rain_ref', how='left')
        
        def _calc_proxy(row):
            lv, hv = row.get('rain_latest_val'), row.get('rain_hist_val')
            if pd.isna(lv) or pd.isna(hv): return "N/A"
            if lv > hv: return "Rising"
            if lv < hv: return "Falling"
            return "Stable"

        res['proxy_trend'] = res.apply(_calc_proxy, axis=1)
        
        def _check_accuracy(row):
            pt, at = row.get('proxy_trend'), row.get('trend_label')
            if pt == "N/A" or not at: return "N/A"
            return "Correct" if pt == at else "Incorrect"
            
        res['proxy_match'] = res.apply(_check_accuracy, axis=1)
        return res
    except Exception as e:
        logger.error(f"Research Data Orchestration Failed: {e}")
        return res
