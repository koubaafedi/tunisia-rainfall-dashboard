import pandas as pd
import numpy as np
import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

from src.data.processing import fetch_uk_data
from src.data.research import fetch_research_data

def run_real_benchmark():
    print("--- 🔬 REAL-WORLD ACCURACY BENCHMARK ---")
    
    # 1. Fetch real ground truth
    df_base = fetch_uk_data(window_days=7)
    if df_base.empty:
        print("No ground truth data.")
        return
        
    df_sample = df_base.head(30)
    
    # 2. Run Calibrated Model
    df_res = fetch_research_data(df_sample, window_days=7)
    
    # 3. Analyze
    valid = df_res[df_res['proxy_match'] != "N/A"]
    if valid.empty:
        print("No matches computed.")
        return
        
    accuracy = (len(valid[valid['proxy_match'] == 'Correct']) / len(valid)) * 100
    print(f"\nFinal Measured Accuracy: {accuracy:.1f}%")
    print(f"Sample size: {len(valid)}")
    
    # Show some successes
    print("\nRecent Correct Predictions:")
    print(valid[valid['proxy_match'] == 'Correct'][['station_label', 'trend_label', 'proxy_trend', 'reff_val', 'et_applied']].head(5))

if __name__ == "__main__":
    run_real_benchmark()
