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

def render_map(df_day):
    # Inject CSS for transparent markers and improved legend
    st.markdown("""
    <style>
        .map-icon {
            background: rgba(0,0,0,0) !important;
            border: none !important;
            box-shadow: none !important;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)

    st.subheader("🗺️ Carte Interactive")
    
    if df_day.empty or 'latitude' not in df_day.columns:
        st.warning("Pas de données géographiques.")
        return

    m = folium.Map(location=[34.0, 9.5], zoom_start=7, tiles="CartoDB positron")
    
    # Custom Legend (Bottom Right, Styled)
    legend_html = """
    <div style="position: fixed; 
                bottom: 30px; right: 30px; width: 220px; 
                background-color: white; border: 1px solid #ccc; z-index: 9999; 
                font-family: 'Cairo', sans-serif; font-size: 14px;
                padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
    <h5 style="margin: 0 0 10px 0; text-align: center; color: #2c3e50; font-weight:700;">Légende</h5>
    
    <!-- Arrows -->
    <div style="margin-bottom: 8px; font-weight:600; color:#34495e;">Evolution (vs N-1)</div>
    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <i class="fa-solid fa-arrow-up" style="color: #2ecc71; font-size: 18px; margin-right: 12px; width: 20px; text-align: center;"></i> 
        <span style="color:#2ecc71;">En Hausse</span>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 5px;">
        <i class="fa-solid fa-arrow-down" style="color: #e74c3c; font-size: 18px; margin-right: 12px; width: 20px; text-align: center;"></i> 
        <span style="color:#e74c3c;">En Baisse</span>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <i class="fa-solid fa-minus" style="color: #95a5a6; font-size: 18px; margin-right: 12px; width: 20px; text-align: center;"></i> 
        <span style="color:#7f8c8d;">Stable</span>
    </div>

    <!-- Regions -->
    <div style="margin-bottom: 5px; font-weight:600; color:#34495e;">Niveau Nappe (Région)</div>
    <div style="background: linear-gradient(to right, #d7191c, #fdae61, #ffffbf, #abdda4, #2b83ba); height: 8px; width: 100%; border-radius: 4px; margin-bottom:4px;"></div>
    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #7f8c8d;">
        <span>Bas</span>
        <span>Haut</span>
    </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # --- CHOROPLETH LAYER ---
    try:
        geojson_url = "https://raw.githubusercontent.com/riatelab/tunisie/master/data/TN-gouvernorats.geojson"
        
        # Find Gov Column
        gov_cols = [c for c in df_day.columns if 'gouvernorat' in c or 'region' in c or 'gov' in c]
        gov_col = next((c for c in gov_cols if 'fr' in c), gov_cols[0] if gov_cols else None)
        
        if gov_col:
            # Clean names to match GeoJSON (usually Title Case)
            df_day['gov_clean'] = df_day[gov_col].astype(str).str.title().str.strip()
            
            # Group by Gov
            gov_stats = df_day.groupby('gov_clean')['pct'].mean().reset_index()
            
            folium.Choropleth(
                geo_data=geojson_url,
                name="Niveau Par Région",
                data=gov_stats,
                columns=['gov_clean', 'pct'],
                key_on='feature.properties.gouv_fr', # MATCHED KEY
                fill_color='RdYlBu', # Red to Blue
                fill_opacity=0.3,
                line_opacity=0.2,
                legend_name='Niveau Moyen (%)'
            ).add_to(m)
    except Exception as e:
        print(f"Choropleth Error: {e}")
    
    # --- ARROW MARKERS ---
    name_col = next((c for c in ['nom_ar', 'nom_fr', 'nom', 'station'] if c in df_day.columns), 'station')

    for _, row in df_day.dropna(subset=['latitude', 'longitude']).iterrows():
        # Get logic
        pct = row.get('pct', 0)
        
        # Basic status color (for popup)
        if pct < 60: status_color, status_txt = "#e74c3c", "Critique"
        elif pct < 90: status_color, status_txt = "#f39c12", "Alerte"
        elif pct < 110: status_color, status_txt = "#2ecc71", "Normal"
        else: status_color, status_txt = "#3498db", "Excédentaire"
        
        name = row.get(name_col, "Inconnu")
        rain = row.get('pluvio_du_jour', 0)
        
        # Trend Logic
        current = row.get('cumul_periode', 0)
        prev = row.get('cumul_periode_precedente', 0)
        diff = row.get('diff_year', 0)
        
        # ARROW COLOR & ICON
        if diff > 0:
            arrow_icon = "fa-arrow-up"
            arrow_color = "#2ecc71" # Green
            diff_color = "#2ecc71"
            arrow_char = "⬆️"
        elif diff < 0:
            arrow_icon = "fa-arrow-down"
            arrow_color = "#e74c3c" # Red
            diff_color = "#e74c3c"
            arrow_char = "⬇️"
        else:
            arrow_icon = "fa-minus"
            arrow_color = "#95a5a6" # Grey
            diff_color = "#95a5a6"
            arrow_char = "➡️"
        
        # Marker Icon (Arrow)
        # Using DivIcon with FontAwesome and removing default bg
        icon_html = f"""
        <div style="text-align: center;">
            <i class="fa-solid {arrow_icon}" style="color: {arrow_color}; font-size: 24px; text-shadow: 0 0 2px #fff;"></i>
        </div>
        """
        
        tooltip_html = f"""
        <div style="font-family: 'Cairo'; text-align: right; direction: rtl; width: 220px;">
            <b style="color: #2c3e50; font-size: 16px;">{name}</b>
            <hr style="margin: 5px 0; border-top: 1px solid #eee;">
            <div style="font-size: 13px; line-height: 1.6;">
                💧 Pluie Jour: <b>{rain} mm</b><br>
                📊 État: <span style="color: {status_color}; font-weight: bold;">{status_txt}</span><br>
                📉 Cumul Saison: <b>{current:.1f} mm</b><br>
                ⏮️ Saison Préc: <b>{prev:.1f} mm</b><br>
                ⚖️ Diff: <span style="color: {diff_color}; font-weight: bold;">{arrow_char} {diff:+.1f} mm</span>
            </div>
        </div>
        """
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=icon_html, class_name="map-icon", icon_size=(30, 30)),
            popup=folium.Popup(tooltip_html, max_width=250),
            tooltip=name
        ).add_to(m)
        
    st_folium(m, width=None, height=600)
