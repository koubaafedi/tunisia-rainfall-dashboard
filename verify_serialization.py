import pandas as pd
import numpy as np
import pyarrow as pa
import logging

def verify_serialization():
    print("--- 🧪 SERIALIZATION VERIFICATION ---")
    
    # Mock some data similar to what fetch_research_data returns
    data = {
        'rain_latest_val': [12.5, np.nan, 8.0],
        'et_applied': [5.0, 5.0, 5.0],
        'reff_val': [7.5, np.nan, 3.0],
        'proxy_trend': ["Rising", "N/A", "Falling"]
    }
    df = pd.DataFrame(data)
    
    # Force numeric types like in the fix
    for col in ['rain_latest_val', 'reff_val', 'et_applied']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print("\nColumn Types:")
    print(df.dtypes)
    
    try:
        # This is what Streamlit/Arrow does internally
        table = pa.Table.from_pandas(df)
        print("\n✅ Success: Dataframe is Arrow-compatible!")
    except Exception as e:
        print(f"\n❌ Failure: Serialization failed: {e}")

if __name__ == "__main__":
    verify_serialization()
