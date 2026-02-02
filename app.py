import streamlit as st
import pandas as pd
from src import data, ui, config

# --- INITIALIZATION ---
st.set_page_config(
    page_title="UK Groundwater Dashboard", 
    layout="wide", 
    page_icon="🇬🇧"
)
ui.apply_custom_css()

def initialize_session_state():
    """Ensures all required session state keys are present."""
    if 'current_window_label' not in st.session_state:
        st.session_state.current_window_label = "Today (Morning)"

def clear_data_cache():
    """Purges cached dataframes to force a hard refresh."""
    for key in list(st.session_state.keys()):
        if key.startswith("df_w"):
            del st.session_state[key]
    st.rerun()

initialize_session_state()

# --- SIDEBAR: NAVIGATION & CONTROLS ---
st.sidebar.title("UK Monitoring")
st.sidebar.markdown("---")

# 1. Timeline Slider (Comparison Window)
st.sidebar.subheader("📅 Temporal Comparison")
window_days = st.sidebar.slider(
    "Comparison Offset",
    min_value=0,
    max_value=config.MAX_COMPARISON_DAYS,
    value=14,
    help=f"0 = Morning Baseline | 1-{config.MAX_COMPARISON_DAYS} = Historical Snapshot"
)

# Manage dynamic labels
if window_days == 0:
    st.session_state.current_window_label = "Today (Morning)"
elif window_days == 1:
    st.session_state.current_window_label = "Yesterday"
else:
    st.session_state.current_window_label = f"{window_days} Days Ago"

# 2. Global Data Refresh
if st.sidebar.button("🔄 Full System Refresh"):
    clear_data_cache()

# --- DATA ORCHESTRATION ---
state_key = f"df_w{window_days}"
if state_key not in st.session_state:
    with st.spinner(f"Synchronizing with {st.session_state.current_window_label}..."):
        st.session_state[state_key] = data.fetch_uk_data(window_days=window_days)

df_all = st.session_state[state_key]

# --- MAIN INTERFACE ---
if not df_all.empty:
    # Layer Filtering (Sidebar)
    st.sidebar.header("🔍 Geo-Filters")
    aquifer_options = sorted(df_all['grouping'].unique())
    selected_aquifers = st.sidebar.multiselect("Filter by Aquifer Layer", options=aquifer_options)
    
    df_active = df_all[df_all['grouping'].isin(selected_aquifers)] if selected_aquifers else df_all

    # Header Section
    st.markdown(f"""
        <div style='text-align: center; padding: 10px 0 30px 0;'>
            <h1 style='margin: 0;'>💧 UK Groundwater Intelligence</h1>
            <p style='color: #666; font-size: 1.1rem;'>
                National monitoring against <b>{st.session_state.current_window_label}</b> benchmark
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Dashboard Navigation
    tab_map, tab_research = st.tabs([
        "GroundTruth", 
        "Prediction and Accuracy"
    ])
    
    with tab_map:
        ui.render_metrics(df_active)
        ui.render_map(df_active)



    with tab_research:
        st.subheader("🧪 Ground Truth vs. Effective Recharge Proxy")
        st.info(r"""
            **Mathematical Framework:**
            $$R_{eff} = \max(0, \sum Rainfall - AET)$$
            
            **Trend Determination Logic:**
            - **Rising**: $R_{eff, latest} > R_{eff, historical}$ (Increased infiltration potential)
            - **Falling**: $R_{eff, latest} < R_{eff, historical}$ (Decreased infiltration potential)
        """)
        
        with st.spinner("Linking geospatial proxies and calculating scientific recharge indices..."):
            pet_meta = data.fetch_ea_pet_metadata()
            df_research = data.fetch_research_data(df_active, window_days=window_days)
            
            ui.render_research_metrics(df_research, wapor_meta=pet_meta)
            ui.render_research_map(df_research)
            ui.render_research_table(df_research)

else:
    st.error("Platform Data Link Severed. Please check API connectivity or refresh.")
    if st.button("Reconnect to National API"):
        clear_data_cache()
