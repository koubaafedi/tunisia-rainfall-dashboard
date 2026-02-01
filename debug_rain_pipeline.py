import pandas as pd
import requests
from src import data
from src.data import research
import logging

logging.basicConfig(level=logging.INFO)

try:
    print("1. Fetching GW stations...")
    gw_df = data.fetch_uk_data()
    print(f"   GW Stations found: {len(gw_df)}")
    
    print("\n2. Linking to Rainfall gauges...")
    linked = research.link_stations_geospatially(gw_df)
    rain_refs = linked['rain_ref'].dropna().unique().tolist()
    print(f"   Linked Gauge Refs: {len(rain_refs)}")
    
    if not rain_refs:
        print("   ERROR: No rainfall gauges linked.")
        exit()

    print(f"\n3. Inspecting /measures for first gauge: {rain_refs[0]}")
    # We use parameterName=Rainfall in code, let's see if that's the issue
    url_m = f"https://environment.data.gov.uk/flood-monitoring/id/measures?stationReference={rain_refs[0]}"
    resp_m = requests.get(url_m, timeout=10)
    if resp_m.status_code == 200:
        items = resp_m.json().get('items', [])
        for i in items:
            print(f"   - Parameter: {i.get('parameter')}, ParameterName: {i.get('parameterName')}, ID: {i.get('@id')}")
            if i.get('latestReading'):
                print(f"     Latest Value: {i.get('latestReading', {}).get('value')}")
    
    print("\n4. Testing batch rainfall readings fetch...")
    win = 7
    readings = research.fetch_rainfall_readings(rain_refs[:50], win)
    print(f"   Readings DataFrame Shape: {readings.shape}")
    if not readings.empty:
        print("   Columns:", list(readings.columns))
        print("   Found historical values:", readings['rain_hist_val'].notna().sum())
    else:
        print("   ERROR: Readings dataframe is empty.")

except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
