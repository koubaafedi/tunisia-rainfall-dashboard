import pandas as pd
import requests
import io
import streamlit as st
import datetime
from src.models import StationData

@st.cache_data(ttl=3600)
def load_raw_data() -> pd.DataFrame:
    """Fetches and merges rainfall and station data."""
    rain_url = "https://catalog.agridata.tn/dataset/082abfac-7a9f-4e27-90c7-1621172737c4/resource/e93a4205-84de-47a5-bcdb-e00520b15e10/download/daily_pluvio.csv"
    station_url = "https://catalog.agridata.tn/dataset/liste-des-stations-pluviometriques-en-tunisie/resource/f448a7e2-c321-4cf7-9fc1-1cb89556190d/download/stations_pluviometrie.xls"
    
    try:
        # Load Rain
        r_rain = requests.get(rain_url)
        df_rain = pd.read_csv(io.StringIO(r_rain.content.decode('utf-8')))
        df_rain.columns = df_rain.columns.str.strip().str.lower()
        
        # Load Stations
        r_st = requests.get(station_url)
        df_st = pd.read_excel(io.BytesIO(r_st.content))
        df_st.columns = df_st.columns.str.strip().str.lower()
        
        # Merge columns check
        rain_col = next((c for c in ['station', 'station_name', 'nom_station', 'nom_fr', 'nom_ar'] if c in df_rain.columns), None)
        st_col = next((c for c in ['nom_fr', 'nom', 'station', 'nom_station'] if c in df_st.columns), None)
        
        if not rain_col or not st_col:
            st.error(f"Column mismatch. Rain cols: {list(df_rain.columns)}. Station cols: {list(df_st.columns)}")
            return None
            
        df_rain['merge_key'] = df_rain[rain_col].astype(str).str.strip().str.upper()
        df_st['merge_key'] = df_st[st_col].astype(str).str.strip().str.upper()
        
        df_merged = pd.merge(df_rain, df_st, on='merge_key', how='left')
        
        # Coalesce Coordinates (prefer Station data _y, then Rain data _x)
        if 'latitude' not in df_merged.columns and 'latitude_y' in df_merged.columns:
            df_merged['latitude'] = df_merged['latitude_y'].fillna(df_merged.get('latitude_x'))
            df_merged['longitude'] = df_merged['longitude_y'].fillna(df_merged.get('longitude_x'))

        # Parse Dates
        if 'date' in df_merged.columns:
            df_merged['date_dt'] = pd.to_datetime(df_merged['date'], errors='coerce')
            
        # Fix Numerics
        cols = ['cumul_periode', 'cumul_moy_periode', 'pluvio_du_jour', 'latitude', 'longitude']
        for c in cols:
            if c in df_merged.columns:
                df_merged[c] = pd.to_numeric(df_merged[c], errors='coerce').fillna(0)
                
        # Calculate Logic
        if 'cumul_moy_periode' in df_merged.columns and 'cumul_periode' in df_merged.columns:
            df_merged['pct'] = (df_merged['cumul_periode'] / df_merged['cumul_moy_periode'].replace(0, 1)) * 100
            
        return df_merged

    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return None

def get_status_color(pct: float) -> tuple[str, str]:
    if pct < 60: return "Critique", "#e74c3c" # Red
    elif pct < 90: return "Alerte", "#f39c12"   # Orange
    elif pct < 110: return "Normal", "#2ecc71"  # Green
    return "Excédentaire", "#3498db"            # Blue
