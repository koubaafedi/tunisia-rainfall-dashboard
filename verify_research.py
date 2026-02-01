import pandas as pd
from src import data
import sys

try:
    print("Fetching raw groundwater data...")
    df_gw = data.fetch_uk_data()
    print(f"Active stations: {len(df_gw)}")
    
    print("\nRunning Research Hub orchestration (Window: 7 days)...")
    df_res = data.fetch_research_data(df_gw, window_days=7)
    
    linked = df_res[df_res['rain_ref'].notna()]
    print(f"Successfully linked {len(linked)} stations to rainfall gauges.")
    
    if not linked.empty:
        counts = df_res['proxy_match'].value_counts()
        print(f"\nGlobal Stats:")
        print(counts)
        
        valid = df_res[df_res['proxy_trend'] != "N/A"]
        if not valid.empty:
            example = valid.iloc[0]
            print(f"\nExample VALID Proxy:")
            print(f"  GW Station: {example['station_label']}")
            print(f"  Rain Gauge: {example['rain_label']}")
            print(f"  Rain Latest: {example.get('rain_latest_val')}")
            print(f"  Rain Hist: {example.get('rain_hist_val')}")
            print(f"  Actual GW Trend: {example['trend_label']}")
            print(f"  Predicted (Rain) Trend: {example['proxy_trend']}")
            print(f"  Prediction Accuracy: {example['proxy_match']}")
        else:
            print("\nWARNING: No valid proxy trends calculated (all N/A).")
    else:
        print("WARNING: No geospatial links found.")
        
    print("\nSUCCESS: Research hub logic verified.")
except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
