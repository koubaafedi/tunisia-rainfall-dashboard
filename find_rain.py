import requests
from datetime import datetime

def find_rainy_stations():
    print("Searching for stations with non-zero rainfall today...")
    # Getting readings from today
    url = "https://environment.data.gov.uk/flood-monitoring/data/readings?parameter=rainfall&today&_limit=10000"
    resp = requests.get(url)
    items = resp.json().get('items', [])
    
    rainy = [i for i in items if float(i.get('value', 0)) > 0]
    print(f"Total readings today: {len(items)}")
    print(f"Readings > 0: {len(rainy)}")
    
    if rainy:
        # Get unique measures
        measures = list(set(i['measure'] for i in rainy))
        print(f"Active rainy measures found: {len(measures)}")
        for m in measures[:5]:
            print(f"Rainy Measure: {m}")
    else:
        print("No rainy readings found today via the global endpoint.")

if __name__ == "__main__":
    find_rainy_stations()
