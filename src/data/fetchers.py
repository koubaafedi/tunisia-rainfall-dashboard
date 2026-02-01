import pandas as pd
import requests
import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .. import config

logger = logging.getLogger(__name__)

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_raw_metadata() -> List[Dict]:
    """Fetches combined station metadata items from Hydro and Flood APIs."""
    h_url = config.HYDRO_STATIONS_URL.replace("_limit=5000", "_limit=10000")
    f_url = config.FLOOD_STATIONS_URL
    
    out = []
    try:
        h_resp = requests.get(h_url, timeout=25)
        if h_resp.status_code == 200:
            out.extend([{"item": i, "source": "Hydro"} for i in h_resp.json().get('items', [])])
            
        f_resp = requests.get(f_url, timeout=25)
        if f_resp.status_code == 200:
            out.extend([{"item": i, "source": "Flood"} for i in f_resp.json().get('items', [])])
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
        
    return out

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_READINGS)
def fetch_latest_readings_raw() -> List[Dict]:
    """Fetches raw measure items from the Flood Monitoring API."""
    try:
        resp = requests.get(config.FLOOD_MEASURES_URL, timeout=25)
        if resp.status_code == 200:
            return resp.json().get('items', [])
    except Exception as e:
        logger.error(f"Readings Fetch Error: {e}")
    return []

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_METADATA)
def fetch_historical_snapshot_raw(window_days: int) -> List[Dict]:
    """Fetches historical readings for a specific date offset."""
    try:
        dt = (datetime.utcnow() - timedelta(days=window_days)).strftime('%Y-%m-%d')
        url = config.FLOOD_READINGS_BASE_URL.format(date=dt, limit=10000)
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            return resp.json().get('items', [])
    except Exception as e:
        logger.error(f"Snapshot Fetch Error: {e}")
    return []

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_HISTORY)
def fetch_station_scale(url: str, conversion_factor: float = 1.0) -> dict:
    """Parses station scale data from its specific JSON endpoint."""
    if not url: return {}
    try:
        safe_url = str(url).replace("http://", "https://")
        if not safe_url.endswith(".json"): safe_url += ".json"
        
        d = requests.get(safe_url, timeout=10).json().get('items', {})
        def _p(k):
            o = d.get(k, {})
            if isinstance(o, dict): 
                return {'value': o.get('value', 0) * conversion_factor, 'dateTime': o.get('dateTime', 'N/A')}
            return None
            
        return {
            'maxOnRecord': _p('maxOnRecord'), 
            'minOnRecord': _p('minOnRecord'), 
            'typicalRangeHigh': d.get('typicalRangeHigh', 0) * conv_factor, 
            'typicalRangeLow': d.get('typicalRangeLow', 0) * conv_factor
        }
    except Exception as e:
        logger.debug(f"Scale resolution failed: {e}")
        return {}

@st.cache_data(ttl=config.DEFAULT_CACHE_TTL_HISTORY)
def fetch_station_history(ref: str, days: int = 7, conversion_factor: float = 1.0) -> pd.DataFrame:
    """Retrieves localized history for a single station."""
    try:
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        url = config.STATION_READINGS_URL.format(station=ref, since=since)
        it = requests.get(url, timeout=10).json().get('items', [])
        if not it: return pd.DataFrame()
        
        df = pd.DataFrame(it)
        if df.empty: return df
        df['dateTime'] = pd.to_datetime(df['dateTime'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce') * conversion_factor
        return df.sort_values('dateTime')
    except: 
        return pd.DataFrame()
