import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timedelta
import json

@st.cache_data(ttl=86400) # Cache station metadata for 24 hours
def fetch_stations_metadata() -> pd.DataFrame:
    """Fetches the static national station list (3600+ items) safely."""
    try:
        url = "https://environment.data.gov.uk/hydrology/id/stations?observedProperty=groundwaterLevel&_limit=5000"
        resp = requests.get(url, timeout=25)
        if resp.status_code != 200: return pd.DataFrame()
        
        items = resp.json().get('items', [])
        if not items: return pd.DataFrame()
        
        df = pd.DataFrame(items)
        
        # Safe column mapping
        df['latitude'] = pd.to_numeric(df.get('lat'), errors='coerce')
        df['longitude'] = pd.to_numeric(df.get('long'), errors='coerce')
        df['station_label'] = df.get('label', 'Unknown Station')
        
        # Use wiskiID as primary ref for Hydrology stations as it matches Flood API better
        if 'stationReference' in df.columns and 'wiskiID' in df.columns:
            df['stationReference'] = df['stationReference'].fillna(df['wiskiID'])
        elif 'wiskiID' in df.columns:
            df['stationReference'] = df['wiskiID']
        
        # Ensure stationReference is a string to prevent merge issues
        df['stationReference'] = df['stationReference'].astype(str)
        
        # Fallback for grouping - Ensure it handles both NaN and missing keys correctly
        df['grouping'] = df.get('aquifer').fillna("Unclassified Aquifer")
        # Second pass to catch any literal None or NaN that might have slipped through
        df['grouping'] = df['grouping'].replace({None: "Unclassified Aquifer", "nan": "Unclassified Aquifer"})
        
        # Keep only what we have
        available_cols = ['stationReference', 'station_label', 'latitude', 'longitude', 'grouping']
        for opt in ['aquifer', 'town', 'riverName']:
            if opt in df.columns:
                available_cols.append(opt)
                
        return df[available_cols]
    except Exception as e:
        st.error(f"Metadata Fetch Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600) # Cache live readings for 10 minutes
def fetch_latest_readings() -> pd.DataFrame:
    """Fetches real-time levels safely."""
    try:
        url = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=level&qualifier=Groundwater&_limit=10000"
        resp = requests.get(url, timeout=25)
        meas_data = []
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            for m in items:
                latest = m.get('latestReading', {})
                val = latest.get('value')
                unit = m.get('unitName', 'm')
                
                conv_factor = 1.0
                if unit.lower() in ['mm', 'millimetre', 'millimeter']: conv_factor = 0.001
                elif unit.lower() in ['cm', 'centimetre', 'centimeter']: conv_factor = 0.01

                if val is not None:
                    val = float(val) * conv_factor

                meas_data.append({
                    'stationReference': str(m.get('stationReference')),
                    'measure_url': m.get('@id'),
                    'latest_value': val,
                    'latest_time': latest.get('dateTime'),
                    'conv_factor': conv_factor
                })
        return pd.DataFrame(meas_data)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_trends_data(df_base: pd.DataFrame) -> pd.DataFrame:
    """Calculates deltas and trends safely."""
    try:
        if df_base.empty or 'measure_url' not in df_base.columns:
            return df_base
            
        today_url = "https://environment.data.gov.uk/flood-monitoring/data/readings?today&parameter=level&qualifier=Groundwater&_limit=10000"
        resp_today = requests.get(today_url, timeout=15)
        if resp_today.status_code != 200: return df_base
        
        t_items = resp_today.json().get('items', [])
        if not t_items: return df_base
        
        df_today = pd.DataFrame(t_items)
        df_today['value'] = pd.to_numeric(df_today['value'], errors='coerce')
        df_start = df_today.sort_values('dateTime').groupby('measure').first().reset_index()
        df_start = df_start[['measure', 'value']].rename(columns={'measure': 'measure_url', 'value': 'start_value'})
        
        df_merged = pd.merge(df_base, df_start, on='measure_url', how='left')
        
        # Trend calculation logic
        def calc_trend(row):
            lv = float(row.get('latest_value', 0))
            # Start value might need normalization too if it was mm/cm
            # But here we already normalized latest_value. start_value from readings API
            # needs the same conv_factor.
            cf = row.get('conv_factor', 1.0)
            sv = float(row.get('start_value', lv / cf if cf else lv)) * cf 
            
            diff = lv - sv
            threshold = 0.002
            if diff > threshold: return "⬆️", "#2ecc71", "Rising"
            if diff < -threshold: return "⬇️", "#e74c3c", "Falling"
            return "➡️", "#95a5a6", "Stable"
        
        df_merged[['trend_icon', 'trend_color', 'trend_label']] = df_merged.apply(
            lambda r: pd.Series(calc_trend(r)), axis=1
        )
        
        df_merged['daily_delta'] = df_merged['latest_value'] - (df_merged['start_value'].fillna(df_merged['latest_value'] / df_merged['conv_factor'].fillna(1.0)) * df_merged['conv_factor'].fillna(1.0))
            
        return df_merged
    except:
        return df_base

def fetch_uk_data(param_type: str = "level") -> pd.DataFrame:
    """Unified entry point with robust error handling and caching."""
    try:
        df_st = fetch_stations_metadata()
        df_meas = fetch_latest_readings()

        if df_st.empty:
            st.warning("National station metadata not available.")
            return pd.DataFrame()
        
        if not df_meas.empty:
            df_meas = df_meas.drop_duplicates(subset=['stationReference'])
            # Inner join to show only stations with ACTIVE measures
            df_merged = pd.merge(df_st, df_meas, on='stationReference', how='inner')
        else:
            return pd.DataFrame()

        # Add trends
        df_final = fetch_trends_data(df_merged)
        
        # Final cleanup
        if 'trend_icon' not in df_final.columns:
            df_final['trend_icon'], df_final['trend_color'], df_final['trend_label'] = "➡️", "#95a5a6", "Stable"
            df_final['daily_delta'] = 0.0

        return df_final.dropna(subset=['latitude', 'longitude'])
    except Exception as e:
        st.error(f"Data Pipeline Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_station_history(station_reference: str, days: int = 7, conv_factor: float = 1.0) -> pd.DataFrame:
    """Fetches unit-normalized history."""
    try:
        since_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        url = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{station_reference}/readings?since={since_date}&_sorted&_limit=1000"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return pd.DataFrame()
            
        readings = resp.json().get('items', [])
        if not readings: return pd.DataFrame()
        
        df = pd.DataFrame(readings)
        df['dateTime'] = pd.to_datetime(df['dateTime'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce') * conv_factor
        return df.sort_values('dateTime')
    except:
        return pd.DataFrame()
