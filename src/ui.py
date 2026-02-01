import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import altair as alt
from typing import Optional, Dict, Any, List
from . import config

def apply_custom_css():
    """Injects high-end, premium CSS tokens."""
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Poppins', sans-serif;
            color: {config.THEME_COLORS["text_main"]};
        }}
        
        .stApp {{
            background-color: {config.THEME_COLORS["background"]};
        }}
        
        /* Metric Card Premium Styling */
        div[data-testid="stMetric"] {{
            background: #ffffff;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.04);
            border: 1px solid #f0f0f0;
            transition: transform 0.2s ease;
        }}
        
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            border-color: {config.THEME_COLORS["primary"]};
        }}
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 24px;
        }}
        
        .marker-badge {{
            background-color: white;
            border-radius: 50%;
            box-shadow: 0 4px 10px rgba(0,0,0,0.12);
            border: 2px solid #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            transition: all 0.2s ease;
        }}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)

def render_metrics(df: pd.DataFrame):
    """Displays key performance indicators."""
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("🛰️ Network Size", f"{len(df)} Stations")
    
    with c2:
        val = df['latest_value'].mean() if not df.empty else 0
        st.metric("💧 Average Level", f"{val:.3f} m")
    
    with c3:
        health = st.session_state.get('health_score', 100)
        st.metric("📡 Data Health", f"{health:.1f}%", help="Reporting activity in last 24h")
    
    with c4:
        peak = st.session_state.get('national_max', 0)
        st.metric("🏔️ National Peak", f"{peak:.2f} m", help="Active national record level")
    
    st.markdown("<br>", unsafe_allow_html=True)

def _generate_map_legend() -> str:
    """Helper to build HTML map legend."""
    items = ""
    for label, color in [("Rising", config.THEME_COLORS["rising"]), 
                        ("Falling", config.THEME_COLORS["falling"]), 
                        ("Stable", config.THEME_COLORS["stable"])]:
        icon = config.MARKER_ICONS[label]
        items += f'''
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <div class="marker-badge" style="margin-right:12px; width:28px; height:28px;">
                <i class="fa {icon}" style="color:{color}; font-size:12px;"></i>
            </div>
            <span style="font-size:12px; font-weight:500;">{label}</span>
        </div>'''
        
    return f'''
    <div style="position: fixed; bottom: 40px; right: 20px; width: 180px; 
                background: white; border-radius: 12px; z-index: 1000; 
                padding: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border: 1px solid #eee;">
        <h6 style="margin: 0 0 12px 0; font-weight:700; color:#444;">Trend Window</h6>
        {items}
    </div>'''

def _create_popup_html(row: pd.Series) -> str:
    """Encapsulates detailed station popup logic with safety checks for missing data."""
    lv = row.get('latest_value', 0)
    hv = row.get('hist_value_norm')
    delta = row.get('period_delta', 0)
    window = st.session_state.get('current_window_label', 'Today')
    
    # Handle missing historical data
    has_history = not pd.isna(hv)
    hv_display = f"{hv:.3f}m" if has_history else "N/A"
    delta_display = f"{'+' if delta > 0 else ''}{delta:.3f}m" if has_history else "No Baseline"
    
    color = config.THEME_COLORS["rising"] if delta > 0 and has_history else (
        config.THEME_COLORS["falling"] if delta < 0 and has_history else config.THEME_COLORS["stable"]
    )
    icon = "fa-arrow-up" if delta > 0 and has_history else (
        "fa-arrow-down" if delta < 0 and has_history else "fa-minus"
    )

    return f"""
    <div style="font-family: 'Poppins'; width: 240px; padding: 5px;">
        <b style="font-size:14px; color:#1a1a1a;">{row['station_label']}</b><br>
        <span style="color:#666; font-size:11px;">{row['grouping']}</span>
        <hr style="margin: 10px 0; border:0; border-top: 1px solid #eee;">
        <div style="margin-bottom: 8px;">
            <span style="color:#888; font-size:11px;">Latest Elevation:</span><br>
            <span style="font-size:20px; font-weight:700; color:{config.THEME_COLORS["primary"]}">
                {lv:.3f} m
            </span>
        </div>
        <div style="background: #f8f9fa; padding: 8px; border-radius: 8px; border-left: 3px solid {color};">
            <span style="color:#777; font-size:10px;">{window}: {hv_display}</span><br>
            <span style="color:{color}; font-weight:700; font-size:14px;">
                {delta_display} <i class="fa {icon}"></i>
            </span>
        </div>
        <div style="font-size:10px; color:#aaa; margin-top:12px; padding-top:8px; border-top:1px dashed #eee;">
            <b>ID:</b> {row['stationReference']} | <b>Since:</b> {str(row['date_opened'])[:10]}
        </div>
    </div>"""

def render_map(df: pd.DataFrame):
    """Renders the main geospatial interactive map."""
    st.subheader("🗺️ National Observation Network")
    
    m = folium.Map(location=[53.0, -2.0], zoom_start=6, tiles="CartoDB positron", zoom_control=True)
    m.get_root().html.add_child(folium.Element(_generate_map_legend()))

    for _, row in df.iterrows():
        icon_label = row.get('trend_label', 'Stable')
        fa_icon = config.MARKER_ICONS.get(icon_label, 'fa-minus')
        color = row.get('trend_color', config.THEME_COLORS["stable"])
        
        icon_html = f'<div class="marker-badge"><i class="fa-solid {fa_icon}" style="color:{color}"></i></div>'
        
        folium.Marker(
            [row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=icon_html, icon_size=(32, 32)),
            popup=folium.Popup(_create_popup_html(row), max_width=300),
            tooltip=row['station_label']
        ).add_to(m)

    st_folium(m, width="100%", height=600, returned_objects=[], key="uk_network_map")

def render_charts(df: pd.DataFrame):
    """Visualizes distribution of stations across aquifer layers."""
    if df.empty:
        st.info("Insufficient data for regional analytics.")
        return

    st.markdown("### 📊 Network Distribution")
    
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        x=alt.X('grouping:N', sort='-y', title="Aquifer Layer"),
        y=alt.Y('count()', title="Station Count"),
        color=alt.Color('grouping:N', legend=None, scale=alt.Scale(scheme='blues')),
        tooltip=['grouping', 'count()']
    ).properties(height=350)
    
    st.altair_chart(chart, use_container_width=True)

def render_station_history(df_hist: pd.DataFrame, label: str, scale_data: Optional[Dict] = None):
    """Renders high-precision time-series charts with record overlays."""
    if df_hist.empty:
        st.info("No localized history found for this station.")
        return

    st.markdown(f"#### 📈 Evolution: {label}")
    
    # Base chart with gradient area
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
        x=alt.X('dateTime:T', title="Timeline"),
        y=alt.Y('value:Q', title="Water Level (m)", scale=alt.Scale(zero=False)),
        tooltip=['dateTime', 'value']
    )

    if scale_data:
        h_max = scale_data.get('maxOnRecord', {})
        if h_max and h_max.get('value'):
            ref_val = h_max['value']
            line = alt.Chart(pd.DataFrame({'y': [ref_val]})).mark_rule(
                color=config.THEME_COLORS["falling"], strokeDash=[4,4], size=1.5
            ).encode(y='y:Q')
            chart = chart + line

    st.altair_chart(chart.properties(height=350).interactive(), use_container_width=True)
    
    if scale_data:
        c1, c2, c3 = st.columns(3)
        h_max, h_min = scale_data.get('maxOnRecord', {}), scale_data.get('minOnRecord', {})
        c1.caption(f"🏆 Record High: **{h_max.get('value', 0):.2f}m**")
        c2.caption(f"📉 Record Low: **{h_min.get('value', 0):.2f}m**")
        c3.caption(f"📏 Range: **{scale_data.get('typicalRangeLow', 0):.1f}m** to **{scale_data.get('typicalRangeHigh', 0):.1f}m**")

def render_data_table(df: pd.DataFrame):
    """Presents flattened data for export."""
    window = st.session_state.get('current_window_label', 'Period')
    cols = ['station_label', 'grouping', 'town', 'riverName', 'latest_value', 'period_delta']
    
    fmt_df = df[[c for c in cols if c in df.columns]].copy()
    fmt_df = fmt_df.rename(columns={'period_delta': f'Delta ({window})'})
    
    st.dataframe(fmt_df, use_container_width=True)
    st.download_button("📥 Download Snapshot (CSV)", df.to_csv(index=False), "groundwater_data.csv")
