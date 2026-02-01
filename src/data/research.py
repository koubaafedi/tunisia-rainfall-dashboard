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

# Constants for Hydrological Calibration
KC_FACTOR = 0.5        # Land Cover Coefficient (Potential ET -> Actual ET)
LAG_DAYS = 7           # Reduced geological lag to ensure API data availability
RAIN_COEFF = 1.0       # Calibration factor for rainfall volume

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
        'dekad_code': 'EA PET 2025 (Calibrated)',
        'caption': f'EA 1km Grid | Kc={KC_FACTOR} | Lag={LAG_DAYS}d',
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d')
    }

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def get_station_specific_et(station_ref: str, month: int) -> float:
    """Retrieves the scientific monthly average PET for a specific station from the aggregated EA dataset."""
    try:
        csv_path = os.path.join("src", "data", "station_pet_averages.csv")
        if not os.path.exists(csv_path):
            return 45.0
            
        df = pd.read_csv(csv_path)
        match = df[(df['stationReference'] == str(station_ref).upper()) & (df['month'] == month)]
        if not match.empty:
            # Result is mm/day (multiplied by Kc to represent Actual ET)
            return float(match['avg_daily_pet'].iloc[0]) * KC_FACTOR * 30.0
    except Exception as e:
        logger.warning(f"PET Lookup failed for {station_ref}: {e}")
        
    return 45.0 * KC_FACTOR 

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_rainfall_metadata() -> pd.DataFrame:
    """Fetches all ACTIVE rainfall monitoring stations in the UK."""
    # 1. Fetch measures to find who is actually reporting
    url_m = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=rainfall&_limit=10000"
    try:
        resp = requests.get(url_m, timeout=25)
        if resp.status_code != 200: return pd.DataFrame()
        items = resp.json().get('items', [])
        
        # Filter for measures with recent readings and get their station refs
        active_refs = set()
        for i in items:
            l_reading = i.get('latestReading')
            if l_reading:
                # Check if it was in the last 14 days
                dt_str = l_reading.get('dateTime')
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    if (datetime.utcnow() - dt).days < 14:
                        active_refs.add(str(i.get('stationReference')))
                        
        # 2. Fetch stations and filter by active_refs
        url_s = "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall&_limit=5000"
        resp_s = requests.get(url_s, timeout=25)
        if resp_s.status_code == 200:
            s_items = resp_s.json().get('items', [])
            df = pd.DataFrame(s_items)
            res = pd.DataFrame()
            res['rain_station_ref'] = df.get('stationReference').astype(str)
            res['rain_latitude'] = pd.to_numeric(df.get('lat'), errors='coerce')
            res['rain_longitude'] = pd.to_numeric(df.get('long'), errors='coerce')
            res['rain_label'] = df.get('label', 'Unknown Rain Gauge')
            
            # Keep only verified active stations
            filtered = res[res['rain_station_ref'].isin(active_refs)]
            logger.info(f"Verified {len(filtered)} active rainfall stations out of {len(res)} total.")
            return filtered.dropna(subset=['rain_latitude', 'rain_longitude'])
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
    """Fetches accumulated rainfall totals using a single-stream fetch and Python-side windowing."""
    if not rain_refs: return pd.DataFrame()
    target_refs = list(set(str(r) for r in rain_refs if r))
    
    # Define lagged windows for partitioning
    # We fetch everything since the start of the historical window
    now = datetime.utcnow()
    hist_start = now - timedelta(days=LAG_DAYS + 2 * window_days + 1) # +1 overlap for safety
    latest_cutoff = now - timedelta(days=LAG_DAYS)
    mid_cutoff = now - timedelta(days=LAG_DAYS + window_days)
    hist_cutoff = now - timedelta(days=LAG_DAYS + 2 * window_days)

    since_str = hist_start.strftime('%Y-%m-%d')

    try:
        # 1. Map stationRefs to Measure URLs (Prefers Tipping Bucket)
        url_m = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=rainfall&_limit=10000"
        resp = requests.get(url_m, timeout=25)
        if resp.status_code != 200: return pd.DataFrame()
        
        items = resp.json().get('items', [])
        # We want to prefer tipping_bucket_raingauge if available
        measure_map = {}
        for i in items:
            ref = str(i.get('stationReference'))
            if not ref or ref not in target_refs: continue
            m_id = i.get('@id')
            label = str(i.get('label', '')).lower()
            
            # Priority: Tipping Bucket > Total > Anything else
            current_prio = 0
            if 'tipping' in label: current_prio = 3
            elif 'total' in label: current_prio = 2
            elif 'rainfall' in label: current_prio = 1
            
            best_m = measure_map.get(ref, (None, -1))
            if current_prio > best_m[1]:
                measure_map[ref] = (m_id, current_prio)

        ref_to_measure = {k: v[0] for k, v in measure_map.items()}
        
        def _fetch_accumulated(ref):
            m_url = ref_to_measure.get(ref)
            if not m_url: return None
            res = {'rain_ref': ref, 'rain_latest_val': 0.0, 'rain_hist_val': 0.0}
            try:
                # Fetch all readings since the start of our longest window
                r_url = f"{m_url}/readings?since={since_str}&_limit=10000"
                resp = requests.get(r_url, timeout=12)
                if resp.status_code == 200:
                    it = resp.json().get('items', [])
                    if not it:
                        logger.warning(f"No readings found for {ref} at {m_url} since {since_str}")
                    for reading in it:
                        val = float(reading.get('value', 0))
                        dt_str = reading.get('dateTime')
                        if not dt_str: continue
                        
                        # Strip 'Z' and parse
                        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        dt = dt.replace(tzinfo=None) # Keep naive for comparison

                        if mid_cutoff <= dt < latest_cutoff:
                            res['rain_latest_val'] += val
                        elif hist_cutoff <= dt < mid_cutoff:
                            res['rain_hist_val'] += val
                else:
                    logger.error(f"API Error {resp.status_code} for {ref} at {m_url}")
                
                return res
            except Exception as e:
                logger.error(f"Exc for {ref}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=30) as executor:
            combined = list(executor.map(_fetch_accumulated, list(ref_to_measure.keys())))
        
        results = [r for r in combined if r]
        if results:
            final = pd.DataFrame(results)
            logger.info(f"Rainfall Pipeline: Calibrated data for {len(final)} gauges.")
            return final
            
    except Exception as e:
        logger.error(f"Rainfall Pipeline Critical Error: {e}")
        
    return pd.DataFrame()

def fetch_research_data(gw_df: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """Orchestrates the linking and proxy calculation for the research hub with hydrological calibration."""
    if gw_df.empty: return gw_df
    
    res = gw_df.copy()
    for col in ['proxy_trend', 'proxy_match', 'rain_ref', 'rain_label', 'rain_dist_km', 'reff_val', 'et_applied']:
        if col not in res.columns:
            res[col] = "N/A" if col in ['proxy_trend', 'proxy_match'] else (np.nan if col != 'rain_label' else "No Gauge Linked")

    try:
        # 1. Spatial Join
        linked = link_stations_geospatially(gw_df)
        if 'rain_ref' not in linked.columns: return res
        
        active_rain_refs = linked['rain_ref'].dropna().unique().tolist()
        if not active_rain_refs: return linked
            
        # 2. Accumulated Rainfall Fetch with Lag
        rain_readings = fetch_rainfall_readings(active_rain_refs, window_days)
        if rain_readings.empty: return linked
        
        # 3. Scientific Calibration (AET = PET * Kc)
        current_month = datetime.utcnow().month
        calibrated = pd.merge(linked, rain_readings, on='rain_ref', how='left')
        calibrated['et_source'] = f"EA Calibrated (Kc={KC_FACTOR}, Lag={LAG_DAYS}d)"
        
        def _calc_recharge_proxy(row):
            lv, hv = row.get('rain_latest_val'), row.get('rain_hist_val')
            if pd.isna(lv) or pd.isna(hv): return "N/A", np.nan
            
            s_ref = row.get('stationReference')
            # get_station_specific_et now includes KC_FACTOR already
            et_total = get_station_specific_et(s_ref, current_month)
            et_scaled = (et_total / 30.0) * window_days
            
            # Reff = Max(0, (Rain * Coeff) - AET)
            reff_latest = max(0.0, (lv * RAIN_COEFF) - et_scaled)
            reff_hist = max(0.0, (hv * RAIN_COEFF) - et_scaled)
            
            if reff_latest > reff_hist: return "Rising", reff_latest
            if reff_latest < reff_hist: return "Falling", reff_latest
            return "Stable", reff_latest

        def _get_trend_str(row):
            lv, hv = row.get('rain_latest_val'), row.get('rain_hist_val')
            if pd.isna(lv) or pd.isna(hv): return "N/A"
            if lv > hv: return "Rising"
            if lv < hv: return "Falling"
            return "Stable"

        # Apply Model
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
        
        # Stabilization
        numeric_cols = ['rain_latest_val', 'rain_hist_val', 'reff_val', 'et_applied', 'rain_dist_km']
        for col in numeric_cols:
            if col in calibrated.columns:
                calibrated[col] = pd.to_numeric(calibrated[col], errors='coerce')
        
        return calibrated

    except Exception as e:
        logger.error(f"Research Calibration Failed: {e}")
        return res
