import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

def apply_custom_css():
    """Injects custom CSS to fix visibility and style."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Cairo', sans-serif;
            color: #2c3e50; /* Dark blue text */
        }
        
        .stApp {
            background-color: #f0f2f6; /* Light gray background */
        }
        
        /* Metric Cards */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            text-align: center;
            border: 1px solid #e1e4e8;
        }
        
        /* Fix label color (was white on white) */
        div[data-testid="stMetricLabel"] {
            font-size: 1rem;
            color: #7f8c8d !important; 
        }
        
        /* Fix value color */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
            color: #2c3e50 !important;
            font-weight: 700;
        }

        h1, h2, h3 {
            color: #2c3e50;
            text-align: center;
        }
        
        /* Map container */
        iframe {
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    st.title("💧 Ressources Hydrauliques Tunisie")
    st.markdown("<h4 style='text-align: center; color: #7f8c8d;'>Surveillance et Analyse Quotidienne</h4>", unsafe_allow_html=True)

def render_metrics(df_day):
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    
    unique_dates = df_day['date_dt'].unique()
    date_str = pd.to_datetime(unique_dates[0]).strftime('%d-%m-%Y') if len(unique_dates) > 0 else "-"
    
    c1.metric("📅 Date", date_str)
    c2.metric("🔢 Stations", len(df_day))
    
    avg_rain = df_day['pluvio_du_jour'].mean() if 'pluvio_du_jour' in df_day.columns else 0
    c3.metric("🌧️ Moyenne", f"{avg_rain:.1f} mm")
    
    max_rain = df_day['pluvio_du_jour'].max() if 'pluvio_du_jour' in df_day.columns else 0
    c4.metric("⛈️ Max", f"{max_rain:.1f} mm")
    st.markdown("---")

def add_legend(m):
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 150px; height: 130px; 
                background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                padding: 10px; border-radius: 10px; opacity: 0.9;">
    <b>Légende (Niveau)</b><br>
    <i style="background:#e74c3c; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Critique (<60%)<br>
    <i style="background:#f39c12; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Alerte (60-90%)<br>
    <i style="background:#2ecc71; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Normal (90-110%)<br>
    <i style="background:#3498db; width:10px; height:10px; display:inline-block; border-radius:50%;"></i> Excédentaire (>110%)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

def render_map(df_day):
    st.subheader("🗺️ Carte Interactive")
    
    if df_day.empty or 'latitude' not in df_day.columns:
        st.warning("Pas de données géographiques.")
        return

    m = folium.Map(location=[34.0, 9.5], zoom_start=7, tiles="CartoDB positron")
    add_legend(m)
    
    # Column mapping logic
    name_col = next((c for c in ['nom_ar', 'nom_fr', 'nom', 'station'] if c in df_day.columns), 'station')

    for _, row in df_day.dropna(subset=['latitude', 'longitude']).iterrows():
        # Get logic
        pct = row.get('pct', 0)
        
        # Color logic
        if pct < 60: color, status = "#e74c3c", "Critique"
        elif pct < 90: color, status = "#f39c12", "Alerte"
        elif pct < 110: color, status = "#2ecc71", "Normal"
        else: color, status = "#3498db", "Excédentaire"
        
        name = row.get(name_col, "Inconnu")
        rain = row.get('pluvio_du_jour', 0)
        
        # Trend Logic
        current = row.get('cumul_periode', 0)
        prev = row.get('cumul_periode_precedente', 0)
        diff = row.get('diff_year', 0)
        arrow = row.get('trend_arrow', '➡️')
        
        # Color for diff
        diff_color = "green" if diff >= 0 else "red"
        
        html = f"""
        <div style="font-family: 'Cairo'; text-align: right; direction: rtl; width: 220px;">
            <b style="color: #2c3e50; font-size: 16px;">{name}</b>
            <hr style="margin: 5px 0; border-top: 1px solid #eee;">
            <div style="font-size: 13px; line-height: 1.6;">
                💧 Pluie Jour: <b>{rain} mm</b><br>
                📊 État: <span style="color: {color}; font-weight: bold;">{status}</span><br>
                📉 Cumul Saison: <b>{current:.1f} mm</b><br>
                ⏮️ Saison Préc: <b>{prev:.1f} mm</b><br>
                ⚖️ Diff: <span style="color: {diff_color}; font-weight: bold;">{arrow} {diff:+.1f} mm</span>
            </div>
        </div>
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(html, max_width=250),
            tooltip=name
        ).add_to(m)
        
    st_folium(m, width=None, height=600)
