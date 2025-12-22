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

    # --- RENDER UI ---
    ui.render_metrics(df_day)
    ui.render_map(df_day)
    
    with st.expander("📂 Données Brutes"):
        cols = [c for c in ['date', 'station', 'nom_ar', 'pluvio_du_jour', 'status', 'pct'] if c in df_day.columns]
        st.dataframe(df_day[cols] if cols else df_day)

else:
    st.error("Impossible de charger les données. Vérifiez la connexion ou le format des fichiers.")
