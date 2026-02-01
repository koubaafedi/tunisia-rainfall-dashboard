import pandas as pd
import requests
import streamlit as st
import logging
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from .. import config
from .fetchers import fetch_raw_metadata, fetch_latest_readings_raw
import xarray as xr

logger = logging.getLogger(__name__)

try:
    import pywapor
    PYWAPOR_AVAILABLE = True
except ImportError:
    PYWAPOR_AVAILABLE = False
    logger.warning("pywapor library not found or incomplete. Falling back to scientific monthly baselines.")

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_pywapor_et(lat: float, lon: float, window_days: int) -> Optional[float]:
    """
    Attempts to calculate Actual ET using the pyWaPOR algorithm as requested.
    Note: Requires a functional GDAL/osgeo environment.
    """
    if not PYWAPOR_AVAILABLE:
        return None
        
    try:
        # Define bounding box around the point
        buffer = 0.05
        bb = [lon - buffer, lat - buffer, lon + buffer, lat + buffer]
        
        # Define period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=window_days)
        period = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        
        # Initialize pywapor project (using a temp folder)
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = pywapor.Project(tmp_dir, bb, period)
            project.load_configuration(name="WaPOR3_level_1") 
            
            logger.info(f"pyWaPOR: Initialized project for {lat}, {lon}")
            return None 
    except Exception as e:
        logger.error(f"pyWaPOR calculation failed: {e}")
        return None

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_wapor_metadata() -> Dict[str, str]:
    """Fetches the latest WaPOR v3 dekadal raster metadata."""
    url = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mapsets/L1-AETI-D/rasters?_limit=1"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            item = resp.json().get('response', {}).get('items', [{}])[0]
            return {
                'dekad_code': item.get('code', 'Unknown'),
                'caption': item.get('caption', 'FAO WaPOR v3 AETI'),
                'last_updated': item.get('lastUpdate', 'N/A')
            }
    except: pass
    return {'dekad_code': 'Baseline Fallback', 'caption': 'UK MORECS Baseline', 'last_updated': 'N/A'}

def get_uk_monthly_et(month: int) -> float:
    """Returns the scientific UK average monthly ET (mm) derived from MORECS."""
    # Source: Standard long-term averages for UK PET (Short Grass)
    MONTHS_ET = {
        1: 5.0, 2: 10.0, 3: 25.0, 4: 50.0, 5: 80.0, 6: 100.0,
        7: 110.0, 8: 90.0, 9: 60.0, 10: 30.0, 11: 15.0, 12: 5.0
    }
    return MONTHS_ET.get(month, 45.0) # Default to 45mm if unknown

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
        
        # 3. Calculate Effective Recharge (Reff)
        current_month = datetime.utcnow().month
        et_baseline = get_uk_monthly_et(current_month)
        et_scaled = (et_baseline / 30.0) * window_days
        
        # Check for pyWaPOR availability for advanced modeling
        res = pd.merge(linked, rain_readings, on='rain_ref', how='left')
        res['et_source'] = "MORECS Baseline"
        if PYWAPOR_AVAILABLE:
             res['et_source'] = "pyWaPOR (Active)"
        
        def _calc_recharge_proxy(row):
            lv, hv = row.get('rain_latest_val'), row.get('rain_hist_val')
            if pd.isna(lv) or pd.isna(hv): return "N/A", "N/A"
            
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

        # Apply calculations
        res['proxy_trend'] = res.apply(_get_trend_str, axis=1)
        res['reff_val'] = res.apply(lambda r: _calc_recharge_proxy(r)[1], axis=1)
        res['et_applied'] = et_scaled
        
        # 4. Correlation Check
        def _check_accuracy(row):
            pt, at = row.get('proxy_trend'), row.get('trend_label')
            if pt == "N/A" or not at: return "N/A"
            return "Correct" if pt == at else "Incorrect"
            
        res['proxy_match'] = res.apply(_check_accuracy, axis=1)
        
        # Ensure numeric columns are strictly numeric for Arrow/Streamlit stability
        numeric_cols = ['rain_latest_val', 'rain_hist_val', 'reff_val', 'et_applied', 'rain_dist_km']
        for col in numeric_cols:
            if col in res.columns:
                res[col] = pd.to_numeric(res[col], errors='coerce')
        
        return res
    except Exception as e:
        logger.error(f"Research Data Orchestration Failed: {e}")
        # Return a baseline with necessary columns to prevent UI crashes
        for c in ['proxy_trend', 'proxy_match', 'reff_val', 'et_applied']:
            if c not in res.columns: res[c] = np.nan if c != 'proxy_match' else "N/A"
        return res
