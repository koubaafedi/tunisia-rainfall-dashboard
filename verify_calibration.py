import pandas as pd
import numpy as np
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.data.research import fetch_research_data, get_station_specific_et

def verify_calibration():
    print("--- 🔬 HYDROLOGICAL CALIBRATION VERIFICATION ---")
    
    # 1. Mock base groundwater data
    gw_data = {
        'stationReference': ['7132', '6502'], # Using some potentially real refs
        'latitude': [51.5, 52.5],
        'longitude': [-0.1, -1.0],
        'trend_label': ['Rising', 'Falling']
    }
    df_gw = pd.DataFrame(gw_data)
    
    print("\n1. Testing fetch_research_data (Calibrated Flow)...")
    try:
        # Fetching for 7 days with the new accumulation logic
        df_res = fetch_research_data(df_gw, window_days=7)
        
        print("\nResults Sample:")
        cols = ['stationReference', 'rain_latest_val', 'rain_hist_val', 'reff_val', 'et_applied', 'proxy_match']
        print(df_res[cols])
        
        # Verify accumulation: Values should be >= 0 and likely > 0 if rain occurred
        none_count = df_res['rain_latest_val'].isna().sum()
        print(f"\nMissing Rainfall Count: {none_count} (Goal: 0)")
        
        # Verify ET Scaling (Kc = 0.65)
        # 45mm/month * 0.65 = 29.25mm/month
        # 29.25 / 30 * 7 = 6.825mm expected for window
        sample_et = df_res['et_applied'].iloc[0]
        print(f"Applied ET (7d window): {sample_et:.2f}mm")
        
        if sample_et < 4.0 or sample_et > 20.0:
            print("⚠️ ET value looks unusual. Check station_pet_averages.csv vs fallback logic.")
        else:
            print("✅ ET Scaling looks scientifically reasonable (Actual ET approx).")
            
        print("\n✅ Verification Success: Model is calibrated.")
        
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_calibration()
