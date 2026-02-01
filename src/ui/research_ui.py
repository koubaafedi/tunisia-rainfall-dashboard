import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from .. import config

def render_research_metrics(df: pd.DataFrame, wapor_meta: dict = None):
    """Displays analytical metrics for the proxy index research."""
    if df.empty: return
    
    valid = df[df['proxy_match'] != "N/A"]
    if valid.empty:
        st.info("No valid proxy correlations found in the current window.")
        return
        
    correct_count = len(valid[valid['proxy_match'] == "Correct"])
    total_count = len(valid)
    accuracy = (correct_count / total_count) * 100
    
    # Showcase WaPOR context in sidebar if available
    if wapor_meta:
        with st.sidebar:
            st.divider()
            st.markdown(f"### 🛰️ FAO WaPOR Context")
            st.info(f"**Latest Dekad:** {wapor_meta.get('dekad_code')}\n\n**Data:** {wapor_meta.get('caption')}")
            st.caption(f"Last API Probe: {wapor_meta.get('last_updated')}")

    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 Prediction Accuracy", f"{accuracy:.1f}%", help="Percentage of stations where Effective Recharge (R_eff) trend matches Ground Truth.")
    c2.metric("🛰️ Linked Gauges", f"{df['rain_ref'].nunique()} unique", help="Number of distinct rainfall stations linked as proxies.")
    c3.metric("📏 Avg Subtraction (ET)", f"{df['et_applied'].mean():.1f} mm", help=f"Source: {df['et_source'].iloc[0] if 'et_source' in df.columns else 'Baseline'}")

def _get_proxy_popup(row: pd.Series) -> str:
    """HTML for research popup comparing ground truth vs proxy."""
    gw_trend = row.get('trend_label', 'Stable')
    px_trend = row.get('proxy_trend', 'N/A')
    match = row.get('proxy_match', 'N/A')
    
    # Metrics (Handle potential NaN/Missing values)
    rain_val = row.get('rain_latest_val')
    et_val = row.get('et_applied', 0.0)
    reff_val = row.get('reff_val')
    
    # Pre-format for HTML display
    fmt_rain = f"{rain_val:.1f}" if pd.notna(rain_val) else "N/A"
    fmt_et = f"{et_val:.1f}" if pd.notna(et_val) else "0.0"
    fmt_reff = f"{reff_val:.1f}" if pd.notna(reff_val) else "N/A"
    
    color_map = {"Rising": config.THEME_COLORS["rising"], "Falling": config.THEME_COLORS["falling"], "Stable": config.THEME_COLORS["stable"], "N/A": "#aaa"}
    match_color = "#2ecc71" if match == "Correct" else ("#e74c3c" if match == "Incorrect" else "#aaa")

    return f"""
    <div style="font-family: 'Poppins'; width: 260px; padding: 5px;">
        <b style="font-size:14px; color:#1a1a1a;">{row['station_label']}</b><br>
        <span style="color:#666; font-size:11px;">Proxy: {row.get('rain_label', 'Unknown Rain Gauge')}</span>
        <hr style="margin: 10px 0; border:0; border-top: 1px solid #eee;">
        
        <table style="width:100%; border-collapse: collapse;">
            <tr>
                <td style="font-size:11px; color:#888;">Actual Trend (GW):</td>
                <td style="font-size:12px; font-weight:700; color:{color_map.get(gw_trend)}">{gw_trend}</td>
            </tr>
            <tr>
                <td style="font-size:11px; color:#888;">Predicted Trend:</td>
                <td style="font-size:12px; font-weight:700; color:{color_map.get(px_trend)}">{px_trend}</td>
            </tr>
        </table>
        
        <div style="margin: 5px 0; font-size:10px; color:#555; background:#f8f9fa; padding: 5px; border-radius:4px;">
            <b>Hydraulic Balance:</b><br>
            Rain ({fmt_rain}mm) - ET ({fmt_et}mm) = <b>Recharge: {fmt_reff}mm</b>
        </div>
        
        <div style="margin-top:10px; padding: 8px; border-radius: 8px; background: {match_color}22; border: 1px solid {match_color}; text-align:center;">
             <span style="color:{match_color}; font-weight:700; font-size:12px;">Predection: {match}</span>
        </div>
        
        <div style="font-size:10px; color:#aaa; margin-top:12px;">
            Distance to Proxy: {row.get('rain_dist_km', 0):.2f}km
        </div>
    </div>"""

def render_research_map(df: pd.DataFrame):
    """Renders the research map showing proxy accuracy and comparisons."""
    st.subheader("🧪 Proxy Correlation Map")
    st.caption("Circles represent Groundwater stations. Color indicates if the Rainfall Proxy correctly predicted the Groundwater trend.")
    
    m = folium.Map(location=[53.0, -2.0], zoom_start=6, tiles="CartoDB positron")
    
    for _, row in df.iterrows():
        match = row.get('proxy_match', 'N/A')
        color = "#2ecc71" if match == "Correct" else ("#e74c3c" if match == "Incorrect" else "#95a5a6")
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=2,
            popup=folium.Popup(_get_proxy_popup(row), max_width=300),
            tooltip=f"{row['station_label']} ({match})"
        ).add_to(m)
        
    st_folium(m, width="100%", height=600, returned_objects=[], key="research_proxy_map")

def render_research_table(df: pd.DataFrame):
    """Shows raw proxy comparison data."""
    st.subheader("📋 Proxy Comparison Dataset")
    st.caption("Detailed breakdown of the scientific hydraulic balance for each linked station.")
    
    cols = [
        'station_label', 'trend_label', 'proxy_trend', 'proxy_match', 
        'rain_latest_val', 'et_applied', 'reff_val', 'rain_label', 'rain_dist_km'
    ]
    fmt_df = df[[c for c in cols if c in df.columns]].copy()
    
    # Clean renaming for user clarity
    fmt_df = fmt_df.rename(columns={
        'station_label': 'GW Station',
        'trend_label': 'Actual Trend (GW)',
        'proxy_trend': 'Predicted Trend (Reff)',
        'proxy_match': 'Accuracy Status',
        'rain_latest_val': 'Rainfall (mm)',
        'et_applied': 'ET Subtracted (mm)',
        'reff_val': 'Effective Recharge (mm)',
        'rain_label': 'Linked Gauge',
        'rain_dist_km': 'Dist (km)'
    })
    
    st.dataframe(fmt_df, width='stretch', hide_index=True)
