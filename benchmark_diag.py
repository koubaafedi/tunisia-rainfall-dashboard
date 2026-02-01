import pandas as pd
import numpy as np
import os
import sys
import logging
import requests

# Add project root to path
sys.path.append(os.getcwd())

from src.data.research import fetch_research_data, link_stations_geospatially

def run_diagnostic():
    print("--- 🔍 RAINFALL DIAGNOSTIC ---")
    
    # 1. Mock a few GW stations 
    test_data = [
        {'stationReference': '7132', 'latitude': 51.5, 'longitude': -0.1, 'trend_label': 'Stable'},
        {'stationReference': '6502', 'latitude': 52.5, 'longitude': -1.0, 'trend_label': 'Stable'}
    ]
    df_test = pd.DataFrame(test_data)
    
    # 2. Check Linking
    print("Linking stations...")
    linked = link_stations_geospatially(df_test)
    print("Linked data:")
    print(linked[['stationReference', 'rain_ref', 'rain_label', 'rain_dist_km']])
    
    # 3. Fetch Research Data (Calculations)
    print("\nOrchestrating research data...")
    df_res = fetch_research_data(df_test, window_days=7)
    
    print("\nResults:")
    cols = ['stationReference', 'rain_ref', 'rain_latest_val', 'rain_hist_val', 'et_applied', 'reff_val']
    print(df_res[cols])
    
    # 4. Deep Dive into one rain_ref
    if not df_res.empty:
        sample_ref = df_res['rain_ref'].dropna().iloc[0]
        print(f"\n--- Deep Dive into Rain Ref: {sample_ref} ---")
        url_ms = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{sample_ref}/measures"
        resp = requests.get(url_ms)
        ms = resp.json().get('items', [])
        print(f"Measures at station {sample_ref}:")
        for m in ms:
            print(f"- {m.get('label')} ({m.get('parameterName')}): {m.get('@id')}")

if __name__ == "__main__":
    run_diagnostic()
