import streamlit as st
import datetime
import pandas as pd
from src import data, ui

# --- PAGE SETUP ---
st.set_page_config(page_title="Ressources Hydrauliques", layout="wide", page_icon="💧")
ui.apply_custom_css()

# --- DATA LOADING ---
df = data.load_raw_data()

# --- MAIN LAYOUT ---
ui.render_header()

if df is not None:
    # --- FILTERS ---
    st.sidebar.header("🔍 Filtres")
    
    if 'date_dt' in df.columns:
        dates = df['date_dt'].dropna().sort_values().unique()
        if len(dates) > 0:
            selected_date = st.sidebar.select_slider(
                "📅 Date",
                options=dates,
                value=dates[-1],
                format_func=lambda d: pd.to_datetime(d).strftime('%d/%m/%Y')
            )
            df_day = df[df['date_dt'] == selected_date]
        else:
            df_day = df # No dates found
    else:
        df_day = df

    # --- ADVANCED FILTERS ---
    st.sidebar.markdown("---")
    st.sidebar.header("🌪️ Filtres Avancés")
    
    # 1. Region Filter
    # Find Gov Col
    gov_cols = [c for c in df_day.columns if 'gouvernorat' in c or 'region' in c or 'gov' in c]
    gov_col = next((c for c in gov_cols if 'fr' in c), gov_cols[0] if gov_cols else None)
    
    if gov_col:
        # Standardize for UI
        df_day[gov_col] = df_day[gov_col].astype(str).str.title().str.strip()
        all_govs = sorted(df_day[gov_col].unique())
        selected_govs = st.sidebar.multiselect("📍 Gouvernorat", options=all_govs, default=[])
        if selected_govs:
            df_day = df_day[df_day[gov_col].isin(selected_govs)]

    # 2. Trend Filter
    if 'trend_category' in df_day.columns:
        all_trends = ['En Hausse', 'En Baisse', 'Stable']
        selected_trends = st.sidebar.multiselect("📈 Tendance", options=all_trends, default=[])
        if selected_trends:
            df_day = df_day[df_day['trend_category'].isin(selected_trends)]
            
    # 3. Rainfall Range Filter
    if 'pluvio_du_jour' in df_day.columns and not df_day.empty:
        min_rain = float(df_day['pluvio_du_jour'].min())
        max_rain = float(df_day['pluvio_du_jour'].max())
        if max_rain > min_rain:
            val_rain = st.sidebar.slider("💧 Pluie (mm)", min_rain, max_rain, (min_rain, max_rain))
            df_day = df_day[
                (df_day['pluvio_du_jour'] >= val_rain[0]) & 
                (df_day['pluvio_du_jour'] <= val_rain[1])
            ]

    # --- RENDER UI ---
    ui.render_metrics(df_day)
    ui.render_map(df_day)
    
    with st.expander("📂 Données Brutes"):
        cols = [c for c in ['date', 'station', 'nom_ar', 'pluvio_du_jour', 'status', 'pct'] if c in df_day.columns]
        st.dataframe(df_day[cols] if cols else df_day)

else:
    st.error("Impossible de charger les données. Vérifiez la connexion ou le format des fichiers.")
