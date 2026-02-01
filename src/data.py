import pandas as pd
import requests
import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _normalize_station_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Standardizes station metadata from any EA source."""
    if df.empty: return pd.DataFrame()
    
    res = pd.DataFrame()
    
    # Identifier Priority
    # In Hydrology, Reading IDs (SU09_56A) often appear in wiskiID or stationReference. 
    # In Flood Monitoring, they appear in stationReference.
    ids = [df.get(c) for c in ['stationReference', 'wiskiID', 'notation'] if c in df.columns]
    if not ids: return pd.DataFrame()
    
    # Coalesce: find first non-null ID
    res['stationReference'] = ids[0]
    for i in ids[1:]:
        res['stationReference'] = res['stationReference'].fillna(i)
        
    res['stationReference'] = res['stationReference'].astype(str).str.upper()
    
    # Coordinates
    res['latitude'] = pd.to_numeric(df.get('lat'), errors='coerce')
    res['longitude'] = pd.to_numeric(df.get('long'), errors='coerce')
    
    # Attribution
    res['station_label'] = df.get('label', 'Unknown Station')
    res['grouping'] = df.get('aquifer', 'Unclassified Aquifer')
    res['date_opened'] = df.get('dateOpened', 'Unknown')
    res['town'] = df.get('town')
    res['riverName'] = df.get('riverName')
    res['stageScale_url'] = df.get('stageScale')
    
    status = df.get('status', 'Active')
    res['is_active'] = status.apply(lambda x: 'Active' in str(x))
    
    return res

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_stations_metadata() -> pd.DataFrame:
    """Aggregates national station metadata for full coverage."""
    try:
        # Fetch from both APIs with sufficient limits
        h_url = config.HYDRO_STATIONS_URL.replace("_limit=5000", "_limit=10000")
        h_resp = requests.get(h_url, timeout=25)
        f_resp = requests.get(config.FLOOD_STATIONS_URL, timeout=25)
        
        h_df = _normalize_station_df(pd.DataFrame(h_resp.json().get('items', [])), "Hydro") if h_resp.status_code == 200 else pd.DataFrame()
        f_df = _normalize_station_df(pd.DataFrame(f_resp.json().get('items', [])), "Flood") if f_resp.status_code == 200 else pd.DataFrame()
        
        if h_df.empty and f_df.empty: return pd.DataFrame()
        
        # Merge sources: Union all stations
        combined = pd.concat([h_df, f_df], ignore_index=True)
        # Take the first occurrence (preserving Hydro metadata if available first)
        final = combined.groupby('stationReference').first().reset_index()
        
        # Coordinate Guard
        return final.dropna(subset=['latitude', 'longitude'])
    except Exception as e:
        logger.error(f"Metadata Aggregation Failed: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_READINGS)
def fetch_latest_readings() -> pd.DataFrame:
    try:
        resp = requests.get(config.FLOOD_MEASURES_URL, timeout=25)
        items = resp.json().get('items', []) if resp.status_code == 200 else []
        
        out = []
        for it in items:
            latest = it.get('latestReading', {})
            val = latest.get('value')
            if val is None: continue
            
            unit = str(it.get('unitName', 'm')).lower()
            conv = 0.001 if 'mm' in unit else (0.01 if 'cm' in unit else 1.0)
            
            out.append({
                'stationReference': str(it.get('stationReference', '')).upper(),
                'measure_url': it.get('@id'),
                'latest_value': float(val) * conv,
                'latest_time': latest.get('dateTime'),
                'conv_factor': conv
            })
        return pd.DataFrame(out)
    except: return pd.DataFrame()

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_historical_snapshot(window_days: int) -> pd.DataFrame:
    try:
        dt = (datetime.utcnow() - timedelta(days=window_days)).strftime('%Y-%m-%d')
        url = config.FLOOD_READINGS_BASE_URL.format(date=dt, limit=10000)
        resp = requests.get(url, timeout=20)
        items = resp.json().get('items', []) if resp.status_code == 200 else []
        if not items: return pd.DataFrame()
        df = pd.DataFrame(items)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return (df.sort_values('dateTime')
                  .groupby('measure')
                  .first()
                  .reset_index()[['measure', 'value']]
                  .rename(columns={'measure': 'measure_url', 'value': 'hist_value'}))
    except: return pd.DataFrame()

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_READINGS)
def fetch_trends_data(df: pd.DataFrame, window_days: int = 0) -> pd.DataFrame:
    if df.empty or 'measure_url' not in df.columns: return df
    try:
        if window_days == 0:
            resp = requests.get(config.FLOOD_TODAY_URL, timeout=15)
            items = resp.json().get('items', []) if resp.status_code == 200 else []
            if not items: return df
            df_pts = pd.DataFrame(items)
            df_pts['value'] = pd.to_numeric(df_pts['value'], errors='coerce')
            pts = df_pts.sort_values('dateTime').groupby('measure').first().reset_index()[['measure', 'value']].rename(columns={'measure': 'measure_url', 'value': 'hist_value'})
        else:
            pts = fetch_historical_snapshot(window_days)
            if pts.empty: return df

        dm = pd.merge(df, pts, on='measure_url', how='left')
        dm['hist_value_norm'] = dm['hist_value'] * dm['conv_factor'].fillna(1.0)
        
        def _get_trend(r):
            lv, hv = float(r.get('latest_value', 0)), float(r.get('hist_value_norm', 0))
            diff = lv - hv
            if diff > config.TREND_THRESHOLD: return "⬆️", config.THEME_COLORS["rising"], "Rising"
            if diff < -config.TREND_THRESHOLD: return "⬇️", config.THEME_COLORS["falling"], "Falling"
            return "➡️", config.THEME_COLORS["stable"], "Stable"
        
        dm[['trend_icon', 'trend_color', 'trend_label']] = dm.apply(lambda r: pd.Series(_get_trend(r)), axis=1)
        dm['period_delta'] = dm['latest_value'] - dm['hist_value_norm'].fillna(dm['latest_value'])
        return dm
    except: return df

def fetch_uk_data(window_days: int = 0) -> pd.DataFrame:
    try:
        meta = fetch_stations_metadata()
        meas = fetch_latest_readings()
        if meta.empty or meas.empty: return pd.DataFrame()
        
        meas = meas.drop_duplicates(subset=['stationReference'])
        merged = pd.merge(meta, meas, on='stationReference', how='inner')
        return fetch_trends_data(merged, window_days=window_days)
    except: return pd.DataFrame()

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_HISTORY)
def fetch_station_scale(url: str, conv: float = 1.0) -> dict:
    if not url: return {}
    try:
        d = requests.get(str(url).replace("http://", "https://") + ".json", timeout=10).json().get('items', {})
        def _p(k):
            o = d.get(k, {})
            if isinstance(o, dict): return {'value': o.get('value', 0)*conv, 'dateTime': o.get('dateTime', 'N/A')}
            return None
        return {'maxOnRecord': _p('maxOnRecord'), 'minOnRecord': _p('minOnRecord'), 'typicalRangeHigh': d.get('typicalRangeHigh', 0)*conv, 'typicalRangeLow': d.get('typicalRangeLow', 0)*conv}
    except: return {}

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_HISTORY)
def fetch_station_history(ref: str, days: int = 7, conv: float = 1.0) -> pd.DataFrame:
    try:
        s = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        it = requests.get(config.STATION_READINGS_URL.format(station=ref, since=s), timeout=10).json().get('items', [])
        if not it: return pd.DataFrame()
        df = pd.DataFrame(it)
        df['dateTime'] = pd.to_datetime(df['dateTime'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce') * conv
        return df.sort_values('dateTime')
    except: return pd.DataFrame()
