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
if 'main_df' not in st.session_state:
    st.session_state.main_df = data.fetch_uk_data()

df = st.session_state.main_df

if st.sidebar.button("🔄 Refresh Data"):
    with st.spinner("Refreshing national data..."):
        st.session_state.main_df = data.fetch_uk_data()
        st.rerun()

if not df.empty:
    # FILTERS
    group_label = "💎 Aquifer Layer"
    all_groups = sorted(df['grouping'].dropna().unique())
    selected_groups = st.sidebar.multiselect(group_label, options=all_groups, default=[])
    
    df_filtered = df[df['grouping'].isin(selected_groups)] if selected_groups else df

    # --- RENDER HEADER ---
    st.markdown(f"""
        <div style='text-align: center; padding: 10px 0 30px 0;'>
            <h1 style='margin: 0;'>💧 UK Groundwater Levels</h1>
            <p style='color: #666; font-size: 1.1rem;'>National monitoring overview of aquifer health</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- RENDER CONTENT ---
    tab_map, tab_charts, tab_data = st.tabs(["🗺️ Live Map", "📊 Regional Analysis", "💾 Data Center"])
    
    with tab_map:
        ui.render_metrics(df_filtered)
        ui.render_map(df_filtered)

    with tab_charts:
        st.subheader("📊 Distribution by Aquifer")
        ui.render_charts(df_filtered)
        
        st.markdown("---")
        
        # We wrap this in a fragment if available (Streamlit 1.33+)
        # This isolates the spinner and chart updates so they don't grey out the map Tab
        @st.fragment
        def render_analysis_section(dff):
            st.subheader("🧐 Individual Station Analysis")
            sel_label = st.selectbox(
                "Select a station to view historical data (7 Days)",
                options=sorted(dff['station_label'].unique()),
                key="station_selector"
            )
            
            if sel_label:
                row = dff[dff['station_label'] == sel_label].iloc[0]
                st_ref = row.get('stationReference')
                cf = row.get('conv_factor', 1.0)
                if st_ref:
                    with st.spinner(f"Loading history for {sel_label}..."):
                        df_h = data.fetch_station_history(st_ref, conv_factor=cf)
                        ui.render_station_history(df_h, sel_label)
                else:
                    st.warning("Historical data reference unavailable.")

        render_analysis_section(df_filtered)

    with tab_data:
        st.subheader("💾 Raw Station Data")
        ui.render_data_table(df_filtered)

else:
    st.error(f"Could not load {page} data. The API might be busy.")
