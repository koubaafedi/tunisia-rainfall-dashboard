import pandas as pd
import numpy as np
import os
import sys
import logging
import requests

# Add project root to path
sys.path.append(os.getcwd())

from src.data.research import fetch_research_data

def run_simple_benchmark():
    print("--- 📊 SCIENTIFIC ACCURACY TEST ---")
    
    # 1. Manually fetch a few active groundwater stations 
    print("Fetching active stations for testing...")
    url = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=level&qualifier=Groundwater&_limit=20"
    try:
        resp = requests.get(url, timeout=15)
        items = resp.json().get('items', [])
        
        test_data = []
        for it in items:
            latest = it.get('latestReading', {})
            val = latest.get('value')
            if val is not None:
                test_data.append({
                    'stationReference': it.get('stationReference'),
                    'latitude': 52.0, # Placeholder lat/lon (will be linked to nearby rain)
                    'longitude': -1.0, 
                    'trend_label': 'Rising' # Dummy assumption to test if proxy returns something
                })
        
        df_test = pd.DataFrame(test_data).head(10)
        
        # 2. Run Calibrated Model
        print(f"Applying model to {len(df_test)} test cases...")
        df_res = fetch_research_data(df_test, window_days=7)
        
        # 3. Analyze Results
        valid = df_res[df_res['proxy_match'] != "N/A"]
        
        print("\n--- MEASURED RESULTS ---")
        if valid.empty:
            print("No valid proxy matches computed. This usually means no nearby rainfall data was found for these points.")
            print("Rainfall values fetched:")
            print(df_res[['stationReference', 'rain_latest_val', 'rain_hist_val']])
        else:
            accuracy = (len(valid[valid['proxy_match'] == "Correct"]) / len(valid)) * 100
            print(f"Computed Accuracy: {accuracy:.1f}%")
            print(df_res[['stationReference', 'rain_latest_val', 'reff_val', 'proxy_match']])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_simple_benchmark()
