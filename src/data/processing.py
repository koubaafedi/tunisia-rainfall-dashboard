import pandas as pd
import logging
import streamlit as st
import requests
from typing import Optional, Dict, Any, List
from .. import config
from .fetchers import (
    fetch_raw_metadata, 
    fetch_latest_readings_raw, 
    fetch_historical_snapshot_raw
)

logger = logging.getLogger(__name__)

def _normalize_station_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Standardizes station metadata items into a clean DataFrame."""
    if df.empty: return pd.DataFrame()
    
    res = pd.DataFrame()
    
    # Identifier Priority: Reading IDs often match 'stationReference' or 'wiskiID'
    ids = [df.get(c) for c in ['stationReference', 'wiskiID', 'notation'] if c in df.columns]
    if not ids: return pd.DataFrame()
    
    res['stationReference'] = ids[0]
    for i in ids[1:]:
        res['stationReference'] = res['stationReference'].fillna(i)
        
    res['stationReference'] = res['stationReference'].astype(str).str.upper()
    
    # Essential Geometry
    res['latitude'] = pd.to_numeric(df.get('lat'), errors='coerce')
    res['longitude'] = pd.to_numeric(df.get('long'), errors='coerce')
    
    # Enrichment Metadata
    res['station_label'] = df.get('label', 'Unknown Station')
    res['grouping'] = df.get('aquifer', 'Unclassified Aquifer')
    res['date_opened'] = df.get('dateOpened', 'Unknown')
    res['town'] = df.get('town')
    res['riverName'] = df.get('riverName')
    res['stageScale_url'] = df.get('stageScale')
    
    status = df['status'] if 'status' in df.columns else pd.Series(['Active'] * len(df))
    res['is_active'] = status.apply(lambda x: 'Active' in str(x))
    
    return res

def fetch_stations_metadata() -> pd.DataFrame:
    """Combines and normalizes metadata from available API sources."""
    raw_items = fetch_raw_metadata()
    if not raw_items: return pd.DataFrame()
    
    dfs = []
    for entry in raw_items:
        normalized = _normalize_station_df(pd.DataFrame([entry['item']]), entry['source'])
        dfs.append(normalized)
        
    if not dfs: return pd.DataFrame()
    
    combined = pd.concat(dfs, ignore_index=True)
    # Deduplicate by ID, keeping the first occurrence (usually Hydro source if sorted)
    final = combined.groupby('stationReference').first().reset_index()
    return final.dropna(subset=['latitude', 'longitude'])

def fetch_latest_readings() -> pd.DataFrame:
    """Retrieves and standardizes live measure data."""
    items = fetch_latest_readings_raw()
    data = []
    for it in items:
        latest = it.get('latestReading', {})
        val = latest.get('value')
        if val is None: continue
        
        unit = str(it.get('unitName', 'm')).lower()
        conv = 0.001 if 'mm' in unit else (0.01 if 'cm' in unit else 1.0)
        
        data.append({
            'stationReference': str(it.get('stationReference', '')).upper(),
            'measure_url': it.get('@id'),
            'latest_value': float(val) * conv,
            'latest_time': latest.get('dateTime'),
            'conv_factor': conv
        })
    return pd.DataFrame(data)

def fetch_historical_snapshot(window_days: int) -> pd.DataFrame:
    """Processes historical reading snapshots for trend baselines."""
    items = fetch_historical_snapshot_raw(window_days)
    if not items: return pd.DataFrame()
    
    df = pd.DataFrame(items)
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    return (df.sort_values('dateTime')
              .groupby('measure')
              .first()
              .reset_index()[['measure', 'value']]
              .rename(columns={'measure': 'measure_url', 'value': 'hist_value'}))

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_READINGS)
def fetch_trends_data(df: pd.DataFrame, window_days: int = 0) -> pd.DataFrame:
    """Calculates trend icons and labels based on historical data comparison."""
    if df.empty or 'measure_url' not in df.columns: return df
    
    # Initialize safe defaults
    df['period_delta'] = 0.0
    df['hist_value_norm'] = df['latest_value'] # Default to no change
    df['trend_icon'] = "➡️"
    df['trend_color'] = config.THEME_COLORS["stable"]
    df['trend_label'] = "Stable"
    
    try:
        # 1. Fetch historical point for comparison
        pts = pd.DataFrame()
        if window_days == 0:
            resp = requests.get(config.FLOOD_TODAY_URL, timeout=15)
            items = resp.json().get('items', []) if resp.status_code == 200 else []
            if items:
                df_pts = pd.DataFrame(items)
                df_pts['value'] = pd.to_numeric(df_pts['value'], errors='coerce')
                pts = df_pts.sort_values('dateTime').groupby('measure').first().reset_index()[['measure', 'value']].rename(columns={'measure': 'measure_url', 'value': 'hist_value'})
        else:
            pts = fetch_historical_snapshot(window_days)

        if pts.empty: 
            return df

        # 2. Merge and Calculate
        # Preserve original DF structure and overwrite defaults where matches exist
        dm = pd.merge(df.drop(columns=['period_delta', 'hist_value_norm', 'trend_icon', 'trend_color', 'trend_label']), 
                      pts, on='measure_url', how='left')
        
        dm['hist_value_norm'] = dm['hist_value'] * dm['conv_factor'].fillna(1.0)
        
        def _get_trend_meta(r):
            lv, hv = float(r.get('latest_value', 0)), float(r.get('hist_value_norm', 0))
            if pd.isna(hv): return "➡️", config.THEME_COLORS["stable"], "Stable"
            diff = lv - hv
            if diff > config.TREND_THRESHOLD: return "⬆️", config.THEME_COLORS["rising"], "Rising"
            if diff < -config.TREND_THRESHOLD: return "⬇️", config.THEME_COLORS["falling"], "Falling"
            return "➡️", config.THEME_COLORS["stable"], "Stable"
        
        dm[['trend_icon', 'trend_color', 'trend_label']] = dm.apply(lambda r: pd.Series(_get_trend_meta(r)), axis=1)
        dm['period_delta'] = dm['latest_value'] - dm['hist_value_norm'].fillna(dm['latest_value'])
        return dm
    except Exception as e:
        logger.error(f"Trend calculation failed: {e}")
        return df

def fetch_uk_data(window_days: int = 0) -> pd.DataFrame:
    """Main orchestrator for updating the entire dashboard state."""
    try:
        meta = fetch_stations_metadata()
        meas = fetch_latest_readings()
        if meta.empty or meas.empty: return pd.DataFrame()
        
        # Inner join to only show stations with active readings
        meas = meas.drop_duplicates(subset=['stationReference'])
        merged = pd.merge(meta, meas, on='stationReference', how='inner')
        return fetch_trends_data(merged, window_days=window_days)
    except Exception as e:
        logger.error(f"Global Data Orchestration Failure: {e}")
        return pd.DataFrame()
