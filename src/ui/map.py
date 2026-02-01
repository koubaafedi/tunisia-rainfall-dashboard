import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from typing import Optional, Dict, Any, List
from .. import config

def _generate_map_legend() -> str:
    """Constructs a professional, floating HTML map legend for trend vectors."""
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
        <h6 style="margin: 0 0 12px 0; font-weight:700; color:#444;">Trend Vectors</h6>
        {items}
    </div>'''

def _create_popup_html(row: pd.Series) -> str:
    """Constructs a high-end HTML popup for station markers with safety fallbacks."""
    lv = row.get('latest_value', 0)
    hv = row.get('hist_value_norm')
    delta = row.get('period_delta', 0)
    window = st.session_state.get('current_window_label', 'Today')
    
    # Validation
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
    """Orchestrates the interactive geospatial layer."""
    st.subheader("🗺️ National Observation Network")
    
    # Initialize Folium Map centered on UK
    m = folium.Map(location=[53.0, -2.0], zoom_start=6, tiles="CartoDB positron", zoom_control=True)
    m.get_root().html.add_child(folium.Element(_generate_map_legend()))

    # Batch add markers
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

    # Render back to Streamlit
    st_folium(m, width="100%", height=600, returned_objects=[], key="uk_groundwater_map")
