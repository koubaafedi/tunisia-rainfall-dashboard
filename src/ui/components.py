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

def render_charts(df: pd.DataFrame):
    """Visualizes the distribution of monitoring sites across aquifer groupings."""
    if df.empty:
        st.info("Insufficient data for network distribution profiling.")
        return

    st.markdown("### 📊 Network Distribution by Layer")
    
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        x=alt.X('grouping:N', sort='-y', title="Aquifer / Geological Layer"),
        y=alt.Y('count()', title="Station Count"),
        color=alt.Color('grouping:N', legend=None, scale=alt.Scale(scheme='blues')),
        tooltip=['grouping', 'count()']
    ).properties(height=350)
    
    st.altair_chart(chart, width='stretch')

def render_station_history(df_hist: pd.DataFrame, label: str, scale_data: Optional[Dict] = None):
    """Renders high-fidelity time-series charts with record overlays."""
    if df_hist is None or df_hist.empty:
        st.info(f"No valid localized history found for {label}.")
        return

    st.markdown(f"#### 📈 Elevation Evolution: {label}")
    
    # Define area chart with primary theme color
    chart = alt.Chart(df_hist).mark_area(
        line={'color': config.THEME_COLORS["primary"]},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='white', offset=0),
                   alt.GradientStop(color=config.THEME_COLORS["primary"], offset=1)],
            x1=1, x2=1, y1=1, y2=0
        ),
        opacity=0.2
    ).encode(
        x=alt.X('dateTime:T', title="Sample Timeline"),
        y=alt.Y('value:Q', title="Water Level (m Elevation)", scale=alt.Scale(zero=False)),
        tooltip=['dateTime', 'value']
    )

    # Optional record high overlay
    if scale_data:
        h_max = scale_data.get('maxOnRecord', {})
        if h_max and h_max.get('value'):
            ref_val = h_max['value']
            line = alt.Chart(pd.DataFrame({'y': [ref_val]})).mark_rule(
                color=config.THEME_COLORS["falling"], strokeDash=[4,4], size=1.5
            ).encode(y='y:Q')
            chart = chart + line

    st.altair_chart(chart.properties(height=350).interactive(), width='stretch')
    
    # Summary stats footer
    if scale_data:
        c1, c2, c3 = st.columns(3)
        h_max, h_min = scale_data.get('maxOnRecord', {}), scale_data.get('minOnRecord', {})
        c1.caption(f"🏆 Record High: **{h_max.get('value', 0):.2f}m**")
        c2.caption(f"📉 Record Low: **{h_min.get('value', 0):.2f}m**")
        range_high = scale_data.get('typicalRangeHigh', 0)
        range_low = scale_data.get('typicalRangeLow', 0)
        c3.caption(f"📏 Typical Range: **{range_low:.1f}m** to **{range_high:.1f}m**")

def render_data_table(df: pd.DataFrame):
    """Present the dataset in a professional, exportable tabular format."""
    window = st.session_state.get('current_window_label', 'Benchmark')
    cols = ['station_label', 'grouping', 'town', 'riverName', 'latest_value', 'period_delta']
    
    fmt_df = df[[c for c in cols if c in df.columns]].copy()
    fmt_df = fmt_df.rename(columns={'period_delta': f'Delta vs {window}'})
    
    st.dataframe(fmt_df, width='stretch')
    st.download_button(
        "📥 Download Observation Snapshot (CSV)", 
        df.to_csv(index=False), 
        "uk_groundwater_snapshot.csv",
        help="Export all active observations to CSV"
    )
