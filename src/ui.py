import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import altair as alt
from folium.plugins import HeatMap

def apply_custom_css():
    """Injects modern, premium CSS."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
            color: #262626;
        }
        
        .stApp {
            background-color: #fcfcfc;
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #f0f0f0;
        }
        
        /* Metric Cards */
        div[data-testid="stMetric"] {
            background: #ffffff;
            padding: 18px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid #efefef;
        }
        
        /* Header Styling */
        h1 { font-weight: 700; color: #1a1a1a; }
        h3 { font-weight: 600; color: #333; }
        
        /* Map Container */
        iframe {
            border-radius: 12px;
            border: 1px solid #eee;
        }
        
        /* Marker Styling */
        .marker-badge {
            background-color: white;
            border-radius: 50%;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            border: 2px solid #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            font-size: 16px;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)

def render_header():
    st.markdown("""
        <div style='text-align: center; padding: 10px 0 30px 0;'>
            <h1 style='margin: 0;'>🇬🇧 UK Groundwater Dashboard</h1>
            <p style='color: #666; font-size: 1.1rem;'>Real-time Hydrological Monitoring via Environment Agency API</p>
        </div>
    """, unsafe_allow_html=True)

def render_metrics(df):
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("🛰️ Active Stations", f"{len(df)}")
    
    avg_level = df['latest_value'].mean() if 'latest_value' in df.columns else 0
    c2.metric("💧 Avg Reading", f"{avg_level:.3f} m")
    
    # Advanced KPIs from Session State
    health = st.session_state.get('health_score', 100)
    c3.metric("📡 Network Health", f"{health:.1f}%", help="Stations reporting in last 24h")
    
    nat_max = st.session_state.get('national_max', 0)
    c4.metric("🏔️ National Peak", f"{nat_max:.2f} m", help="Highest absolute level currently recorded")
    
    st.markdown("<br>", unsafe_allow_html=True)

def render_map(df):
    st.subheader("🗺️ Live Station Network")
    
    if df.empty or 'latitude' not in df.columns:
        st.warning("No geographic data available for the UK pivot.")
        return

    # Center on UK
    m = folium.Map(location=[53.5, -2.5], zoom_start=6, tiles="CartoDB positron")
    
    # Legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; right: 30px; width: 220px; 
                background: white; border: 1px solid #ddd; z-index: 9999; 
                padding: 15px; border-radius: 12px; font-family: 'Poppins', sans-serif;">
        <h5 style="margin: 0 0 10px 0; font-weight:700;">Evolution Trend</h5>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div class="marker-badge" style="margin-right:10px;"><i class="fa fa-arrow-up" style="color:#2ecc71"></i></div>
            <span>Rising Level</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div class="marker-badge" style="margin-right:10px;"><i class="fa fa-arrow-down" style="color:#e74c3c"></i></div>
            <span>Falling Level</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div class="marker-badge" style="margin-right:10px;"><i class="fa fa-minus" style="color:#95a5a6"></i></div>
            <span>Stable</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Add Markers
    for _, row in df.iterrows():
        icon_color = row.get('trend_color', '#95a5a6')
        icon_char = row.get('trend_icon', '➡️')
        
        # Use FontAwesome icons for a cleaner look
        fa_icon = "fa-minus"
        if icon_char == "⬆️": fa_icon = "fa-arrow-up"
        elif icon_char == "⬇️": fa_icon = "fa-arrow-down"
        
        icon_html = f'''
        <div class="marker-badge">
            <i class="fa-solid {fa_icon}" style="color: {icon_color}"></i>
        </div>
        '''
        
        latest_val = row.get('latest_value', 0)
        unit = "m" # Unified
        
        delta = row.get('daily_delta', 0)
        delta_color = "#2ecc71" if delta > 0 else ("#e74c3c" if delta < 0 else "#95a5a6")
        delta_sign = "+" if delta > 0 else ""
        
        popup_html = f"""
        <div style="font-family: 'Poppins'; width: 240px;">
            <b style="color: #1a1a1a; font-size:14px;">{row['station_label']}</b><br>
            <span style="color: #666; font-size:11px;">{row['grouping']}</span><br>
            <hr style="margin: 8px 0;">
            <div style="margin-bottom: 5px;">
                <span style="font-size:16px; font-weight:700;">{latest_val:.3f} {unit}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color:{delta_color}; font-size:13px; font-weight:600;">Today: {delta_sign}{delta:.3f}m</span>
                <span style="color:{icon_color}; font-weight:700; font-size:13px;">{row.get('trend_label', 'Stable')} {icon_char}</span>
            </div>
            <div style="font-size:10px; color:#999; margin-top:10px; border-top: 1px dashed #eee; padding-top:6px;">
                <b>Operational Since:</b> {row.get('date_opened', 'N/A')[:10]}<br>
                <b>Ref:</b> {row.get('stationReference', 'N/A')}
            </div>
        </div>
        """
        
        folium.Marker(
            [row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=icon_html, icon_size=(32, 32)),
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=row['station_label']
        ).add_to(m)

    st_folium(m, width=None, height=600, returned_objects=[], key="main_map")

def render_charts(df):
    if df.empty or 'grouping' not in df.columns:
        st.info("Select items in sidebar to view analytics.")
        return

    group_name = "Aquifer Layer"
    st.markdown(f"### 📊 Stations per {group_name}")
    
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        x=alt.X('grouping:N', sort='-y', title=group_name),
        y=alt.Y('count()', title="Number of Stations"),
        color=alt.Color('grouping:N', legend=None),
        tooltip=['grouping', 'count()']
    ).properties(height=350)
    
    st.altair_chart(chart, use_container_width=True)

def render_station_history(df_hist, station_label, scale_data=None):
    if df_hist.empty:
        st.info("No historical data available for this station.")
        return

    st.markdown(f"#### 📈 Historical Trend: {station_label}")
    
    # Shading for typical range
    base = alt.Chart(df_hist).encode(x=alt.X('dateTime:T', title="Date / Time"))
    
    chart = base.mark_area(
        line={'color':'#2b83ba'},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='white', offset=0),
                   alt.GradientStop(color='#2b83ba', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        ),
        opacity=0.3
    ).encode(
        y=alt.Y('value:Q', title="Water Level (m)", scale=alt.Scale(zero=False)),
        tooltip=['dateTime', 'value']
    )

    final_chart = chart
    
    if scale_data:
        # Add Historical Max Marker
        h_max = scale_data.get('maxOnRecord', {})
        if isinstance(h_max, dict) and h_max.get('value'):
            max_line = alt.Chart(pd.DataFrame({'y': [h_max['value']]})).mark_rule(
                color='#e74c3c', strokeDash=[5,5]
            ).encode(y='y:Q')
            max_label = max_line.mark_text(
                align='left', dx=5, dy=-10, text=f"Max Record: {h_max['value']:.2f}m ({h_max['dateTime'][:10]})", color='#e74c3c'
            ).encode(x=alt.value(0))
            final_chart = final_chart + max_line + max_label

    st.altair_chart(final_chart.properties(height=350).interactive(), use_container_width=True)
    
    if scale_data:
        c1, c2, c3 = st.columns(3)
        h_max = scale_data.get('maxOnRecord', {})
        h_min = scale_data.get('minOnRecord', {})
        c1.write(f"🏆 **Max Record:** {h_max.get('value', 0):.2f}m")
        c2.write(f"📉 **Min Record:** {h_min.get('value', 0):.2f}m")
        c3.write(f"📏 **Typical Range:** {scale_data.get('typicalRangeLow', 0):.1f}m - {scale_data.get('typicalRangeHigh', 0):.1f}m")

def render_data_table(df):
    cols = ['station_label', 'grouping', 'town', 'riverName', 'latest_value', 'daily_delta', 'unit']
    display_df = df[[c for c in cols if c in df.columns]]
    st.dataframe(display_df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Station List (CSV)", csv, "uk_stations.csv", "text/csv")
