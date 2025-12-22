import pandas as pd
import requests
import json
import io

def debug_geojson():
    # 1. Load Data
    print("Loading Data...")
    url_rain = "https://catalog.agridata.tn/dataset/082abfac-7a9f-4e27-90c7-1621172737c4/resource/e93a4205-84de-47a5-bcdb-e00520b15e10/download/daily_pluvio.csv"
    df_rain = pd.read_csv(io.StringIO(requests.get(url_rain).content.decode('utf-8')))
    df_rain.columns = df_rain.columns.str.strip().str.lower()
    
    url_st = "https://catalog.agridata.tn/dataset/liste-des-stations-pluviometriques-en-tunisie/resource/f448a7e2-c321-4cf7-9fc1-1cb89556190d/download/stations_pluviometrie.xls"
    df_st = pd.read_excel(io.BytesIO(requests.get(url_st).content))
    df_st.columns = df_st.columns.str.strip().str.lower()
    
    # Merge keys logic
    rain_col = next((c for c in ['station', 'station_name', 'nom_station', 'nom_fr', 'nom_ar'] if c in df_rain.columns), None)
    st_col = next((c for c in ['nom_fr', 'nom', 'station', 'nom_station'] if c in df_st.columns), None)
    
    df_rain['merge_key'] = df_rain[rain_col].astype(str).str.strip().str.upper()
    df_st['merge_key'] = df_st[st_col].astype(str).str.strip().str.upper()
    df = pd.merge(df_rain, df_st, on='merge_key', how='left')
    
    print("Data Columns:", list(df.columns))
    
    # Try to find gov col
    gov_col = next((c for c in df.columns if 'gouv' in c or 'gov' in c), None)
    print(f"Detected Gov Col: {gov_col}")
    
    if gov_col:
        unique_data_govs = sorted(df[gov_col].astype(str).dropna().unique())
        print("\nData Govs (Sample):", unique_data_govs[:5])
    else:
        print("CRITICAL: No governorate column found!")
        unique_data_govs = []

    # 2. Load GeoJSON
    print("\nLoading GeoJSON...")
    geojson_url = "https://raw.githubusercontent.com/riatelab/tunisie/master/data/TN-gouvernorats.geojson"
    geo_data = requests.get(geojson_url).json()
    
    unique_geo_govs = []
    for feature in geo_data['features']:
        props = feature['properties']
        # Try to find the name key
        name = props.get('gov_name_fr') or props.get('name_fr') or props.get('gouvernorat')
        if name: unique_geo_govs.append(name)
        else: print("WARN: No name property found in feature:", props.keys())

    unique_geo_govs = sorted(list(set(unique_geo_govs)))
    print("GeoJSON Govs (Sample):", unique_geo_govs[:5])
    
    # 3. Intersection
    print("\n--- MATCH CHECK ---")
    data_set = set([str(x).upper() for x in unique_data_govs])
    geo_set = set([str(x).upper() for x in unique_geo_govs])
    
    matches = data_set.intersection(geo_set)
    print(f"Matches: {len(matches)}")
    print("Missing in GeoJSON:", list(data_set - geo_set))

if __name__ == "__main__":
    debug_geojson()
