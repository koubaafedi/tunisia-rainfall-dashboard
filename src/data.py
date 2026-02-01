import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timedelta
import json

@st.cache_data(ttl=900)
def fetch_uk_data(param_type: str = "level") -> pd.DataFrame:
    """
    Fetches UK stations and latest readings with high limits for full coverage.
    Uses 'qualifier=Groundwater' reaching 1000+ locations.
    """
    try:
        # 1. Define URLs
        if param_type == "rainfall":
            st_url = "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=rainfall&_limit=10000"
            meas_url = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=rainfall&_limit=10000"
        else:
            # Use Hydrology API for Stations (3600+ locations nationwide with coords)
            st_url = "https://environment.data.gov.uk/hydrology/id/stations?observedProperty=groundwaterLevel&_limit=5000"
            # Use Flood Monitoring API for Measures (real-time readings)
            meas_url = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=level&qualifier=Groundwater&_limit=10000"

        # 2. Fetch Stations
        resp_st = requests.get(st_url, timeout=25)
        if resp_st.status_code != 200:
            st.error(f"Stations API error: {resp_st.status_code}")
            return pd.DataFrame()
            
        items_st = resp_st.json().get('items', [])
        df_st = pd.DataFrame(items_st)
        
        if df_st.empty:
            return pd.DataFrame()

        # Clean Stations with appropriate mapping for Hydrology/Flood API differences
        df_st['latitude'] = pd.to_numeric(df_st['lat'], errors='coerce')
        df_st['longitude'] = pd.to_numeric(df_st['long'], errors='coerce')
        df_st['station_label'] = df_st['label'].fillna("Unknown")
        
        if param_type == "level":
            # Hydrology API specific: use stationReference or wiskiID for merging
            df_st['stationReference'] = df_st['stationReference'].fillna(df_st.get('wiskiID', ''))
            # Use Aquifer as the primary grouping for groundwater
            df_st['grouping'] = df_st['aquifer'].fillna("Unclassified Aquifer")
        else:
            # Flood API (Rainfall) specific
            df_st['stationReference'] = df_st['stationReference'].fillna(df_st.get('notation', ''))
            # Use Town/Catchment for rainfall
            df_st['grouping'] = df_st.get('town', df_st.get('catchmentName', "General Monitoring"))
        
        # 3. Fetch Measures (contains latestReading)
        resp_meas = requests.get(meas_url, timeout=25)
        meas_data = []
        if resp_meas.status_code == 200:
            items_m = resp_meas.json().get('items', [])
            for m in items_m:
                latest = m.get('latestReading', {})
                val = latest.get('value')
                unit = m.get('unitName', 'm')
                
                # NORMALIZE TO METERS
                # NORMALIZE TO METERS
                conv_factor = 1.0
                if unit.lower() in ['mm', 'millimetre', 'millimeter']:
                    conv_factor = 0.001
                elif unit.lower() in ['cm', 'centimetre', 'centimeter']:
                    conv_factor = 0.01

                if val is not None:
                    val = float(val) * conv_factor

                meas_data.append({
                    'stationReference': m.get('stationReference'),
                    'measure_url': m.get('@id'),
                    'latest_value': val,
                    'latest_time': latest.get('dateTime'),
                    'unit': 'm', # Unify to meter
                    'conv_factor': conv_factor,
                    'station_url_flood': m.get('station')
                })
        df_meas = pd.DataFrame(meas_data)

        # 4. Merge on Station Reference
        if not df_meas.empty:
            df_meas = df_meas.drop_duplicates(subset=['stationReference'])
            # We use a Left join to prioritize the coordinates from Hydrology API
            df_merged = pd.merge(df_st, df_meas, on='stationReference', how='left')
            df_merged['latest_value'] = pd.to_numeric(df_merged['latest_value'], errors='coerce').fillna(0.0)
        else:
            df_merged = df_st.copy()
            df_merged['latest_value'] = 0.0
            df_merged['conv_factor'] = 1.0

        # 5. FETCH REAL TRENDS (Bulk approach for Today)
        # We compare Today's latest reading vs the first reading of today to get a trend.
        try:
            qual_filter = "Groundwater" if param_type == "level" else "rainfall"
            param_filter = "level" if param_type == "level" else "rainfall"
            today_url = f"https://environment.data.gov.uk/flood-monitoring/data/readings?today&parameter={param_filter}&qualifier={qual_filter}&_limit=10000"
            
            resp_today = requests.get(today_url, timeout=15)
            if resp_today.status_code == 200:
                t_items = resp_today.json().get('items', [])
                if t_items:
                    df_today = pd.DataFrame(t_items)
                    df_today['value'] = pd.to_numeric(df_today['value'], errors='coerce')
                    # Get first reading of today for each measure
                    df_start = df_today.sort_values('dateTime').groupby('measure').first().reset_index()
                    df_start = df_start[['measure', 'value']].rename(columns={'measure': 'measure_url', 'value': 'start_value'})
                    
                    df_merged = pd.merge(df_merged, df_start, on='measure_url', how='left')
                    
                    # NORMALIZE START VALUE
                    df_merged['start_value'] = df_merged['start_value'] * df_merged['conv_factor'].fillna(1.0)
                    
                    def calc_trend(row):
                        lv = float(row.get('latest_value', 0))
                        sv = float(row.get('start_value', lv))
                        diff = lv - sv
                        threshold = 0.002 if param_type == "level" else 0.0001
                        if diff > threshold: return "⬆️", "#2ecc71", "Rising"
                        if diff < -threshold: return "⬇️", "#e74c3c", "Falling"
                        return "➡️", "#95a5a6", "Stable"
                    
                    df_merged[['trend_icon', 'trend_color', 'trend_label']] = df_merged.apply(
                        lambda r: pd.Series(calc_trend(r)), axis=1
                    )
                else:
                    df_merged['trend_icon'], df_merged['trend_color'], df_merged['trend_label'] = "➡️", "#95a5a6", "Stable"
            else:
                df_merged['trend_icon'], df_merged['trend_color'], df_merged['trend_label'] = "➡️", "#95a5a6", "Stable"
        except:
             df_merged['trend_icon'], df_merged['trend_color'], df_merged['trend_label'] = "➡️", "#95a5a6", "Stable"

        # Post-process deltas for display
        if 'start_value' in df_merged.columns:
            df_merged['daily_delta'] = df_merged['latest_value'] - df_merged['start_value'].fillna(df_merged['latest_value'])
        else:
            df_merged['daily_delta'] = 0.0

        # Drop stations without coordinates or without real-time measures
        return df_merged.dropna(subset=['latitude', 'longitude', 'measure_url'])

    except Exception as e:
        st.error(f"Global Data Fetch Error: {e}")
        return pd.DataFrame()

def fetch_station_history(station_reference: str, days: int = 7, conv_factor: float = 1.0) -> pd.DataFrame:
    """
    Fetches historical readings for a specific station.
    """
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
