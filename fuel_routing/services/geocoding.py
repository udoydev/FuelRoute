import re
import logging
import requests
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# In-memory cache to avoid duplicate geocoding requests
GEOCODE_CACHE: Dict[str, Tuple[float, float, str]] = {}

# Common US Cities lookup for instant response without network calls
COMMON_US_CITIES: Dict[str, Tuple[float, float, str]] = {
    "new york, ny": (40.712776, -74.005974, "New York, NY, USA"),
    "los angeles, ca": (34.052235, -118.243683, "Los Angeles, CA, USA"),
    "chicago, il": (41.878113, -87.629799, "Chicago, IL, USA"),
    "houston, tx": (29.760427, -95.369804, "Houston, TX, USA"),
    "phoenix, az": (33.448376, -112.074036, "Phoenix, AZ, USA"),
    "philadelphia, pa": (39.952583, -75.165222, "Philadelphia, PA, USA"),
    "san antonio, tx": (29.424122, -98.493629, "San Antonio, TX, USA"),
    "san diego, ca": (32.715736, -117.161087, "San Diego, CA, USA"),
    "dallas, tx": (32.776665, -96.796989, "Dallas, TX, USA"),
    "austin, tx": (30.267153, -97.743057, "Austin, TX, USA"),
    "san jose, ca": (37.338207, -121.886330, "San Jose, CA, USA"),
    "san francisco, ca": (37.774929, -122.419418, "San Francisco, CA, USA"),
    "seattle, wa": (47.606209, -122.332069, "Seattle, WA, USA"),
    "denver, co": (39.739235, -104.990250, "Denver, CO, USA"),
    "washington, dc": (38.907192, -77.036873, "Washington, DC, USA"),
    "boston, ma": (42.360081, -71.058884, "Boston, MA, USA"),
    "miami, fl": (25.761681, -80.191788, "Miami, FL, USA"),
    "atlanta, ga": (33.748997, -84.387985, "Atlanta, GA, USA"),
    "nashville, tn": (36.162663, -86.781601, "Nashville, TN, USA"),
    "detroit, mi": (42.331429, -83.045753, "Detroit, MI, USA"),
    "las vegas, nv": (36.169941, -115.139832, "Las Vegas, NV, USA"),
    "portland, or": (45.515232, -122.678383, "Portland, OR, USA"),
    "orlando, fl": (28.538336, -81.379234, "Orlando, FL, USA"),
    "charlotte, nc": (35.227085, -80.843124, "Charlotte, NC, USA"),
    "indianapolis, in": (39.768402, -86.158066, "Indianapolis, IN, USA"),
    "columbus, oh": (39.961178, -82.998795, "Columbus, OH, USA"),
    "kansas city, mo": (39.099728, -94.578568, "Kansas City, MO, USA"),
    "st. louis, mo": (38.627003, -90.199402, "St. Louis, MO, USA"),
    "saint louis, mo": (38.627003, -90.199402, "Saint Louis, MO, USA"),
    "pittsburgh, pa": (40.440624, -79.995888, "Pittsburgh, PA, USA"),
    "minneapolis, mn": (44.977753, -93.265011, "Minneapolis, MN, USA"),
    "tampa, fl": (27.950575, -82.457178, "Tampa, FL, USA"),
    "new orleans, la": (29.951065, -90.071533, "New Orleans, LA, USA"),
    "cleveland, oh": (41.499321, -81.694361, "Cleveland, OH, USA"),
    "salt lake city, ut": (40.760780, -111.891045, "Salt Lake City, UT, USA"),
    "memphis, tn": (35.149532, -90.048981, "Memphis, TN, USA"),
    "baltimore, md": (39.290386, -76.612190, "Baltimore, MD, USA"),
    "milwaukee, wi": (43.038902, -87.906471, "Milwaukee, WI, USA"),
    "albuquerque, nm": (35.084385, -106.650421, "Albuquerque, NM, USA"),
    "el paso, tx": (31.761877, -106.485023, "El Paso, TX, USA"),
    "oklahoma city, ok": (35.467560, -97.516426, "Oklahoma City, OK, USA"),
    "louisville, ky": (38.252666, -85.758453, "Louisville, KY, USA"),
    "omaha, ne": (41.256538, -95.934502, "Omaha, NE, USA"),
    "raleigh, nc": (35.779591, -78.638176, "Raleigh, NC, USA"),
    "richmond, va": (37.540726, -77.436050, "Richmond, VA, USA"),
    "sacramento, ca": (38.581573, -121.494400, "Sacramento, CA, USA"),
    "tucson, az": (32.222607, -110.974711, "Tucson, AZ, USA"),
    "tulsa, ok": (36.153980, -95.992775, "Tulsa, OK, USA"),
}

COORD_REGEX = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def geocode_location(location_str: str) -> Tuple[float, float, str]:
    """
    Geocodes a location string into (latitude, longitude, display_name).
    Supports:
      1. Coordinates: "30.2672, -97.7431"
      2. City, State: "Austin, TX"
      3. Full addresses
    """
    clean_str = location_str.strip()
    cache_key = clean_str.lower()

    # 1. Check if raw coordinates
    coord_match = COORD_REGEX.match(clean_str)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon, f"Coordinates ({lat:.4f}, {lon:.4f})"

    # 2. Check in-memory cache
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    # 3. Check fast static US city dictionary
    if cache_key in COMMON_US_CITIES:
        result = COMMON_US_CITIES[cache_key]
        GEOCODE_CACHE[cache_key] = result
        return result

    # 4. Query OpenStreetMap Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": clean_str,
            "format": "json",
            "countrycodes": "us",
            "limit": 1
        }
        headers = {
            "User-Agent": "DjangoFuelOptimizationEngine/1.0 (contact@assessment.com)"
        }
        response = requests.get(url, params=params, headers=headers, timeout=6)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                display_name = data[0].get("display_name", clean_str)
                result = (lat, lon, display_name)
                GEOCODE_CACHE[cache_key] = result
                return result
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed for '{clean_str}': {e}")

    # 5. Fallback: Query Photon Geocoder (OSM-based, high rate limits)
    try:
        photon_url = "https://photon.komoot.io/api/"
        params = {"q": clean_str, "limit": 1}
        resp = requests.get(photon_url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"] # [lon, lat]
                lon, lat = coords[0], coords[1]
                props = features[0].get("properties", {})
                name = f"{props.get('name', clean_str)}, {props.get('state', '')}"
                result = (lat, lon, name)
                GEOCODE_CACHE[cache_key] = result
                return result
    except Exception as e:
        logger.warning(f"Photon fallback geocoding failed for '{clean_str}': {e}")

    raise ValueError(f"Unable to geocode location: '{location_str}'. Please provide a valid US city, state or 'lat,lon' coordinates.")
