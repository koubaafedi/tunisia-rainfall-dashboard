import streamlit as st
import pandas as pd
import altair as alt
from typing import Optional, Dict, Any, List
from .. import config

def render_metrics(df: pd.DataFrame):
    """Displays high-level KPIs in a responsive 4-column layout."""
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("🛰️ Network Size", f"{len(df)} Stations")
    
    with c2:
        val = df['latest_value'].mean() if not df.empty else 0
        st.metric("💧 Average Level", f"{val:.3f} m")
    
    with c3:
        health = st.session_state.get('data_health', 100) # Updated from generic session state
        st.metric("📡 Data Health", f"{health:.1f}%", help="Reporting activity in recent window")
    
    with c4:
        peak = df['latest_value'].max() if not df.empty else 0
        st.metric("🏔️ Network Peak", f"{peak:.2f} m", help="Highest current groundwater elevation")
    
    st.markdown("<br>", unsafe_allow_html=True)

