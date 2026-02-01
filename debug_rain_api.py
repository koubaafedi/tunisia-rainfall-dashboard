import requests
import json
from datetime import datetime, timedelta

def debug_rainfall_api():
    # 1. Fetch rainfall measures
    print("Fetching sample rainfall measures with more metadata...")
    url_m = "https://environment.data.gov.uk/flood-monitoring/id/measures?parameter=rainfall&_limit=20"
    resp = requests.get(url_m)
    items = resp.json().get('items', [])
    
    if not items:
        print("No measures found.")
        return

    # Use a wider window and try different date formats
    since_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    for it in items:
        m_id = it.get('@id')
        station_ref = it.get('stationReference')
        label = it.get('label')
        unit = it.get('unitName')
        
        print(f"\n--- Station: {station_ref} | Label: {label} | Unit: {unit} ---")
        print(f"URL: {m_id}")
        
        # Latest
        rl = requests.get(f"{m_id}/readings?latest")
        rl_items = rl.json().get('items', [])
        if rl_items:
            print(f"Latest Reading: {rl_items[0].get('value')} at {rl_items[0].get('dateTime')}")
        else:
            print("Latest Reading: NONE FOUND")
            
        # Accumulated (Try different query param)
        # Some endpoints prefer 'since'
        ra_url = f"{m_id}/readings?since={since_date}&_limit=500"
        ra = requests.get(ra_url)
        if ra.status_code == 200:
            readings = ra.json().get('items', [])
            print(f"Readings found with ISO since: {len(readings)}")
            if readings:
                vals = [float(r['value']) for r in readings if 'value' in r]
                print(f"Sum: {sum(vals)}")
            else:
                # Try simple date
                since_simple = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
                ra_simple = requests.get(f"{m_id}/readings?date={since_simple}")
                print(f"Readings found with ?date={since_simple}: {len(ra_simple.json().get('items', []))}")
        else:
            print(f"Error {ra.status_code}")

if __name__ == "__main__":
    debug_rainfall_api()
