import pandas as pd
import requests
import io

def inspect_data():
    print("--- 1. RAINFALL DATA ---")
    rain_url = "https://catalog.agridata.tn/dataset/082abfac-7a9f-4e27-90c7-1621172737c4/resource/e93a4205-84de-47a5-bcdb-e00520b15e10/download/daily_pluvio.csv"
    try:
        r = requests.get(rain_url)
        df_rain = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        print("Columns:", df_rain.columns.tolist())
        print("First row:", df_rain.iloc[0].to_dict())
    except Exception as e:
        print("Error fetching rain:", e)

    print("\n--- 2. STATIONS DATA ---")
    station_url = "https://catalog.agridata.tn/dataset/liste-des-stations-pluviometriques-en-tunisie/resource/f448a7e2-c321-4cf7-9fc1-1cb89556190d/download/stations_pluviometrie.xls"
    try:
        r = requests.get(station_url)
        df_st = pd.read_excel(io.BytesIO(r.content))
        print("Columns:", df_st.columns.tolist())
        print("First row:", df_st.iloc[0].to_dict())
    except Exception as e:
        print("Error fetching stations:", e)

if __name__ == "__main__":
    inspect_data()
