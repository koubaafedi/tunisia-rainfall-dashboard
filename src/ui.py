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
            color: #2c3e50;
        }
        
        .stApp {
            background-color: #f8f9fa;
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e9ecef;
            box-shadow: 2px 0 5px rgba(0,0,0,0.02);
        }
        
        /* Metric Cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.08);
        }
        
        /* Metric Labels & Values */
        div[data-testid="stMetricLabel"] {
            font-size: 0.9rem;
            color: #6c757d !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        
        div[data-testid="stMetricValue"] {
            font-size: 2rem;
            color: #2c3e50 !important;
            font-weight: 700;
        }

        /* Header Styling */
        h1 {
            font-weight: 700;
            color: #2c3e50;
            letter-spacing: -1px;
        }
        h2, h3, h4 {
            color: #34495e;
        }
        
        /* Map Container */
        iframe {
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border: 1px solid #e9ecef;
        }
        
        /* Map Icons */
        .map-icon {
            background: rgba(0,0,0,0) !important;
            border: none !important;
            box-shadow: none !important;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)

def render_header():
    st.markdown("""
        <div style='text-align: center; padding: 20px 0 30px 0;'>
            <h1 style='margin: 0;'>💧 Ressources Hydrauliques</h1>
            <p style='color: #7f8c8d; font-size: 1.1rem;'>Surveillance et Analyse Quotidienne des Nappes</p>
        </div>
    """, unsafe_allow_html=True)

def render_metrics(df_day):
    c1, c2, c3, c4 = st.columns(4)
    
    unique_dates = df_day['date_dt'].unique()
    date_str = pd.to_datetime(unique_dates[0]).strftime('%d-%m-%Y') if len(unique_dates) > 0 else "-"
    
    c1.metric("📅 Date", date_str)
    c2.metric("🔢 Stations", f"{len(df_day)}")
    
    avg_rain = df_day['pluvio_du_jour'].mean() if 'pluvio_du_jour' in df_day.columns else 0
    c3.metric("🌧️ Moyenne", f"{avg_rain:.1f} mm")
    
    max_rain = df_day['pluvio_du_jour'].max() if 'pluvio_du_jour' in df_day.columns else 0
    c4.metric("⛈️ Max", f"{max_rain:.1f} mm")
    st.markdown("<br>", unsafe_allow_html=True)

def render_map(df_day, show_heatmap=False):
    st.subheader("🗺️ Carte Interactive")
    
    if df_day.empty or 'latitude' not in df_day.columns:
        st.warning("Pas de données géographiques.")
        return

    m = folium.Map(location=[34.0, 9.5], zoom_start=7, tiles="CartoDB positron")
    
    if show_heatmap:
        # HEATMAP LAYER
        heat_data = df_day[['latitude', 'longitude', 'pluvio_du_jour']].dropna().values.tolist()
        HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)
    else:
        # Custom Legend (Bottom Right, Styled)
        legend_html = """
        <div style="position: fixed; 
                    bottom: 30px; right: 30px; width: 220px; 
                    background-color: white; border: 1px solid #ccc; z-index: 9999; 
                    font-family: 'Poppins', sans-serif; font-size: 14px;
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
                df_day['gov_clean'] = df_day[gov_col].astype(str).str.title().str.strip()
                gov_stats = df_day.groupby('gov_clean')['pct'].mean().reset_index()
                
                folium.Choropleth(
                    geo_data=geojson_url,
                    name="Niveau Par Région",
                    data=gov_stats,
                    columns=['gov_clean', 'pct'],
                    key_on='feature.properties.gouv_fr',
                    fill_color='RdYlBu',
                    fill_opacity=0.3,
                    line_opacity=0.2,
                    legend_name='Niveau Moyen (%)'
                ).add_to(m)
        except Exception:
            pass
        
        # --- MARKERS ---
        name_col = next((c for c in ['nom_ar', 'nom_fr', 'nom', 'station'] if c in df_day.columns), 'station')
        for _, row in df_day.dropna(subset=['latitude', 'longitude']).iterrows():
            pct = row.get('pct', 0)
            if pct < 60: status_color, status_txt = "#e74c3c", "Critique"
            elif pct < 90: status_color, status_txt = "#f39c12", "Alerte"
            elif pct < 110: status_color, status_txt = "#2ecc71", "Normal"
            else: status_color, status_txt = "#3498db", "Excédentaire"
            
            name = row.get(name_col, "Inconnu")
            rain = row.get('pluvio_du_jour', 0)
            diff = row.get('diff_year', 0)
            
            if diff > 0: arrow_icon, arrow_color, arrow_char = "fa-arrow-up", "#2ecc71", "⬆️"
            elif diff < 0: arrow_icon, arrow_color, arrow_char = "fa-arrow-down", "#e74c3c", "⬇️"
            else: arrow_icon, arrow_color, arrow_char = "fa-minus", "#95a5a6", "➡️"
            
            icon_html = f"""<div style="text-align: center;"><i class="fa-solid {arrow_icon}" style="color: {arrow_color}; font-size: 24px; text-shadow: 0 0 2px #fff;"></i></div>"""
            
            tooltip = f"""
            <div style="font-family: 'Poppins'; text-align: right; direction: rtl; width: 200px;">
                <b>{name}</b><br>Rain: {rain}mm<br>Diff: <span style="color:{arrow_color}">{arrow_char} {diff:+.1f}</span>
            </div>
            """
            folium.Marker(
                [row['latitude'], row['longitude']],
                icon=folium.DivIcon(html=icon_html, class_name="map-icon", icon_size=(30, 30)),
                popup=folium.Popup(tooltip, max_width=250),
                tooltip=name
            ).add_to(m)

    st_folium(m, width=None, height=600)

def render_charts(df):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Cumul par Gouvernorat")
        # Find Gov Col
        gov_cols = [c for c in df.columns if 'gouvernorat' in c or 'region' in c or 'gov' in c]
        gov_col = next((c for c in gov_cols if 'fr' in c), gov_cols[0] if gov_cols else None)
        
        if gov_col:
            df['gov_clean'] = df[gov_col].astype(str).str.title().str.strip()
            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X('gov_clean', sort='-y', title="Gouvernorat"),
                y=alt.Y('mean(pluvio_du_jour)', title="Pluie Moyenne (mm)"),
                color=alt.Color('mean(pluvio_du_jour)', scale=alt.Scale(scheme='blues')),
                tooltip=['gov_clean', 'mean(pluvio_du_jour)']
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
            
    with col2:
        st.markdown("### 📈 Top 5 Stations (Pluie)")
        if 'pluvio_du_jour' in df.columns:
            name_col = next((c for c in ['nom_ar', 'nom_fr', 'nom', 'station'] if c in df.columns), 'station')
            top5 = df.nlargest(5, 'pluvio_du_jour')[[name_col, 'pluvio_du_jour']]
            st.table(top5.style.format({'pluvio_du_jour': "{:.1f} mm"}))

def render_data_table(df):
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger CSV",
        data=csv,
        file_name='donnees_pluviometrie.csv',
        mime='text/csv',
    )
