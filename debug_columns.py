import pandas as pd
import requests
import io

def check_cols():
    print("--- RAIN DATA ---")
    url = "https://catalog.agridata.tn/dataset/082abfac-7a9f-4e27-90c7-1621172737c4/resource/e93a4205-84de-47a5-bcdb-e00520b15e10/download/daily_pluvio.csv"
    try:
        r = requests.get(url)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        print("Raw Columns:", list(df.columns))
        df.columns = df.columns.str.strip().str.lower()
        print("Lower Columns:", list(df.columns))
        
        found = next((c for c in ['station', 'station_name'] if c in df.columns), None)
        print(f"Found Rain Key: {found}")
    except Exception as e:
        print(e)

    print("\n--- STATIONS DATA ---")
    url2 = "https://catalog.agridata.tn/dataset/liste-des-stations-pluviometriques-en-tunisie/resource/f448a7e2-c321-4cf7-9fc1-1cb89556190d/download/stations_pluviometrie.xls"
    try:
        r = requests.get(url2)
        df = pd.read_excel(io.BytesIO(r.content))
        print("Raw Columns:", list(df.columns))
        df.columns = df.columns.str.strip().str.lower()
        print("Lower Columns:", list(df.columns))
        
        found = next((c for c in ['nom_fr', 'nom', 'station'] if c in df.columns), None)
        print(f"Found Station Key: {found}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_cols()
