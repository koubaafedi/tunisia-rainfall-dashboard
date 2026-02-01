import pandas as pd
import requests
import streamlit as st
import logging
import math
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from .. import config

logger = logging.getLogger(__name__)

# Removed pywapor dependency as requested. Pivoted to EA PET Dataset (2025).

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_ea_pet_metadata() -> Dict[str, str]:
    """Provides metadata about the scientific PET dataset."""
    return {
        'dekad_code': 'EA PET 2025',
        'caption': 'Environment Agency Potential ET (1km Grid)',
        'last_updated': '2026-02-02'
    }

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def get_station_specific_et(station_ref: str, month: int) -> float:
    """Retrieves the scientific monthly average PET for a specific station from the aggregated EA dataset."""
    try:
        csv_path = os.path.join("src", "data", "station_pet_averages.csv")
        if not os.path.exists(csv_path):
            return 45.0 # Fallback to UK national average (Monthly total)
            
        df = pd.read_csv(csv_path)
        match = df[(df['stationReference'] == str(station_ref).upper()) & (df['month'] == month)]
        if not match.empty:
            # avg_daily_pet is mm/day
            return float(match['avg_daily_pet'].iloc[0]) * 30.0 # Monthly total
    except Exception as e:
        logger.warning(f"PET Lookup failed for {station_ref}: {e}")
        
    return 45.0 # Scientific monthly average fallback (MORECS baseline approx)

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
            logger.warning(f"Rainfall Pipeline: Coverage {len(final)}/{len(target_refs)} gauges.")
            return final
            
    except Exception as e:
        logger.error(f"Rainfall Pipeline Critical Error: {e}")
        
    return pd.DataFrame()

def fetch_research_data(gw_df: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """Orchestrates the linking and proxy calculation for the research hub."""
    if gw_df.empty: return gw_df
    
    # Initialize basic res to guarantee structure
    res = gw_df.copy()
    for col in ['proxy_trend', 'proxy_match', 'rain_ref', 'rain_label', 'rain_dist_km', 'reff_val', 'et_applied']:
        if col not in res.columns:
            res[col] = "N/A" if col in ['proxy_trend', 'proxy_match'] else (np.nan if col != 'rain_label' else "No Gauge Linked")

    try:
        # 1. Spatial Join
        linked = link_stations_geospatially(gw_df)
        if 'rain_ref' not in linked.columns: return res
        
        active_rain_refs = linked['rain_ref'].dropna().unique().tolist()
        if not active_rain_refs: 
            return linked.assign(proxy_trend="N/A", proxy_match="N/A", reff_val=np.nan, et_applied=np.nan)
            
        # 2. Rainfall Fetch
        rain_readings = fetch_rainfall_readings(active_rain_refs, window_days)
        if rain_readings.empty: 
            return linked.assign(proxy_trend="N/A", proxy_match="N/A", reff_val=np.nan, et_applied=np.nan)
        
        # 3. Scientific Calibration
        current_month = datetime.utcnow().month
        calibrated = pd.merge(linked, rain_readings, on='rain_ref', how='left')
        calibrated['et_source'] = "EA Potential ET (2025 Grid)"
        
        def _calc_recharge_proxy(row):
            lv, hv = row.get('rain_latest_val'), row.get('rain_hist_val')
            if pd.isna(lv) or pd.isna(hv): return "N/A", np.nan
            
            s_ref = row.get('stationReference')
            et_total = get_station_specific_et(s_ref, current_month)
            et_scaled = (et_total / 30.0) * window_days
            
            # Reff = Max(0, Rain - ET)
            reff_latest = max(0.0, lv - et_scaled)
            reff_hist = max(0.0, hv - et_scaled)
            
            if reff_latest > reff_hist: return "Rising", reff_latest
            if reff_latest < reff_hist: return "Falling", reff_latest
            return "Stable", reff_latest

        def _get_trend_str(row):
            lv, hv = row.get('rain_latest_val'), row.get('rain_hist_val')
            if pd.isna(lv) or pd.isna(hv): return "N/A"
            if lv > hv: return "Rising"
            if lv < hv: return "Falling"
            return "Stable"

        # Apply scientific model
        calibrated['proxy_trend_basic'] = calibrated.apply(_get_trend_str, axis=1)
        recharge_results = calibrated.apply(_calc_recharge_proxy, axis=1)
        calibrated['proxy_trend'] = recharge_results.apply(lambda x: x[0])
        calibrated['reff_val'] = recharge_results.apply(lambda x: x[1])
        calibrated['et_applied'] = calibrated.apply(lambda r: (get_station_specific_et(r['stationReference'], current_month) / 30.0) * window_days, axis=1)
        
        # 4. Correlation Accuracy
        def _check_accuracy(row):
            pt, at = row.get('proxy_trend'), row.get('trend_label')
            if pt == "N/A" or not at: return "N/A"
            return "Correct" if pt == at else "Incorrect"
            
        calibrated['proxy_match'] = calibrated.apply(_check_accuracy, axis=1)
        
        # Stabilization: Ensure numeric columns are strictly numeric for Arrow
        numeric_cols = ['rain_latest_val', 'rain_hist_val', 'reff_val', 'et_applied', 'rain_dist_km']
        for col in numeric_cols:
            if col in calibrated.columns:
                calibrated[col] = pd.to_numeric(calibrated[col], errors='coerce')
        
        return calibrated

    except Exception as e:
        logger.error(f"Research Data Orchestration Failed: {e}")
        # Always return the initialized 'res' which has the required columns
        return res
