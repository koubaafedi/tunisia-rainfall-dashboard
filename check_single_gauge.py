import requests
import json

# Known rainfall station to test
TEST_REF = "033707" 

print(f"Checking station {TEST_REF}...")

# 1. Check measures
url_m = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{TEST_REF}/measures"
resp_m = requests.get(url_m, timeout=10)
if resp_m.status_code == 200:
    items = resp_m.json().get('items', [])
    print(f"Found {len(items)} measures.")
    for it in items:
        p_name = it.get('parameterName')
        p_id = it.get('@id')
        l_reading = it.get('latestReading')
        print(f"  - Measure: {p_name}")
        print(f"    ID: {p_id}")
        print(f"    Has latestReading: {l_reading is not None}")
        if l_reading:
            print(f"    Latest Value: {l_reading.get('value')}")
else:
    print(f"Failed to fetch measures: {resp_m.status_code}")

# 2. Check latest readings endpoint for this station
url_r = f"https://environment.data.gov.uk/flood-monitoring/id/stations/{TEST_REF}/readings?latest"
resp_r = requests.get(url_r, timeout=10)
if resp_r.status_code == 200:
    r_items = resp_r.json().get('items', [])
    print(f"\nReadings endpoint returned {len(r_items)} items.")
    if r_items:
        print(f"Sample Reading: {r_items[0]}")
else:
    print(f"Failed to fetch readings: {resp_r.status_code}")
