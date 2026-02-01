import streamlit as st
import pandas as pd
from src import data, ui

# --- PAGE SETUP ---
st.set_page_config(page_title="UK Environmental Dashboard", layout="wide", page_icon="🇬🇧")
ui.apply_custom_css()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🇬🇧 UK Monitoring")
st.sidebar.info("Focus: National Groundwater Monitoring")

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filters")

# --- DATA LOADING ---
param_type = "level"
title_prefix = "Groundwater"
color_scheme = "blues"
page = "💧 Groundwater Levels"

df = data.fetch_uk_data(param_type=param_type)

if not df.empty:
    # FILTERS
    group_label = "💎 Aquifer Layer"
    all_groups = sorted(df['grouping'].dropna().unique())
    selected_groups = st.sidebar.multiselect(group_label, options=all_groups, default=[])
    
    df_filtered = df[df['grouping'].isin(selected_groups)] if selected_groups else df

    # --- RENDER HEADER ---
    st.markdown(f"""
        <div style='text-align: center; padding: 10px 0 30px 0;'>
            <h1 style='margin: 0;'>{page}</h1>
            <p style='color: #666; font-size: 1.1rem;'>National overview of {title_prefix.lower()} monitoring stations</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- RENDER CONTENT ---
    tab_map, tab_charts, tab_data = st.tabs(["🗺️ Live Map", "📊 Regional Analysis", "💾 Data Center"])
    
    with tab_map:
        ui.render_metrics(df_filtered)
        ui.render_map(df_filtered)

    with tab_charts:
        st.subheader(f"📊 {title_prefix} Distribution")
        
        # Aggregate view
        ui.render_charts(df_filtered)
        
        st.markdown("---")
        # Individual Station History
        st.subheader("🧐 Individual Station Analysis")
        selected_station_label = st.selectbox(
            "Select a station to view historical data (7 Days)",
            options=sorted(df_filtered['station_label'].unique()),
            index=0 if not df_filtered.empty else None
        )
        
        if selected_station_label:
            station_row = df_filtered[df_filtered['station_label'] == selected_station_label].iloc[0]
            st_ref = station_row.get('stationReference')
            cf = station_row.get('conv_factor', 1.0)
            if st_ref:
                with st.spinner(f"Fetching history for {selected_station_label}..."):
                    df_hist = data.fetch_station_history(st_ref, conv_factor=cf)
                    ui.render_station_history(df_hist, selected_station_label)
            else:
                st.warning("This station does not support historical readings via this ID.")

    with tab_data:
        st.subheader("💾 Raw Station Data")
        ui.render_data_table(df_filtered)

else:
    st.error(f"Could not load {page} data. The API might be busy.")
