"""
Configuration module for the UK Groundwater Dashboard.
Centralizes API endpoints, thresholds, and styling parameters.
"""

# --- API ENDPOINTS ---
HYDRO_STATIONS_URL = (
    "https://environment.data.gov.uk/hydrology/id/stations"
    "?_limit=5000"
)

FLOOD_MEASURES_URL = (
    "https://environment.data.gov.uk/flood-monitoring/id/measures"
    "?parameter=level&qualifier=Groundwater&_limit=10000"
)

FLOOD_STATIONS_URL = (
    "https://environment.data.gov.uk/flood-monitoring/id/stations"
    "?parameter=level&qualifier=Groundwater&_limit=5000"
)

# Base for historical snapshots: {past_date} and {limit} to be formatted
FLOOD_READINGS_BASE_URL = (
    "https://environment.data.gov.uk/flood-monitoring/data/readings"
    "?date={date}&parameter=level&qualifier=Groundwater&_limit={limit}"
)

FLOOD_TODAY_URL = (
    "https://environment.data.gov.uk/flood-monitoring/data/readings"
    "?today&parameter=level&qualifier=Groundwater&_limit=10000"
)

# Station specific reading history
STATION_READINGS_URL = "https://environment.data.gov.uk/flood-monitoring/id/stations/{station}/readings?since={since}&_sorted&_limit=1000"

# --- OPERATIONAL THRESHOLDS ---
TREND_THRESHOLD = 0.002  # meters (2mm) to detect Rising/Falling
DEFAULT_CACHE_TTL_METADATA = 86400  # 24 hours
DEFAULT_CACHE_TTL_READINGS = 600    # 10 minutes
DEFAULT_CACHE_TTL_HISTORY = 3600    # 1 hour

# --- UI STYLING ---
THEME_COLORS = {
    "primary": "#2b83ba",
    "rising": "#2ecc71",
    "falling": "#e74c3c",
    "stable": "#95a5a6",
    "background": "#fcfcfc",
    "text_main": "#1a1a1a",
    "text_muted": "#666"
}

MARKER_ICONS = {
    "Rising": "fa-arrow-up",
    "Falling": "fa-arrow-down",
    "Stable": "fa-minus"
}

# --- FILTERS ---
MAX_COMPARISON_DAYS = 28
DEFAULT_STATION_HISTORY_DAYS = 7
