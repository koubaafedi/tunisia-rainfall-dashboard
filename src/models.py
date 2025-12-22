from dataclasses import dataclass
from typing import Optional

@dataclass
class StationData:
    """Represents a single station's data for a specific day."""
    name_fr: str
    name_ar: str
    lat: float
    lon: float
    rainfall_24h: float
    status_label: str
    status_color: str
    trend: str = "Stable"
    rain_season: float = 0.0
