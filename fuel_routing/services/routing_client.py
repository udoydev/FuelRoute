import logging
import requests
import numpy as np
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

EARTH_RADIUS_MILES = 3958.8


def haversine_vectorized(lats1: np.ndarray, lons1: np.ndarray, lats2: np.ndarray, lons2: np.ndarray) -> np.ndarray:
    """
    Computes great-circle distance in miles between successive points in arrays.
    """
    dlat = np.radians(lats2 - lats1)
    dlon = np.radians(lons2 - lons1)
    a = (np.sin(dlat / 2.0) ** 2 +
         np.cos(np.radians(lats1)) * np.cos(np.radians(lats2)) * np.sin(dlon / 2.0) ** 2)
    return EARTH_RADIUS_MILES * 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def format_duration(seconds: float) -> str:
    """Formats duration in seconds into a friendly 'X hours Y mins' string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours} hr {minutes} min"
    return f"{minutes} min"


def fetch_route_osrm(start_lat: float, start_lon: float, finish_lat: float, finish_lon: float) -> Dict[str, Any]:
    """
    Fetches the driving route between two points using OSRM in exactly ONE HTTP call.
    Returns:
      - total_distance_miles: float
      - duration_seconds: float
      - duration_formatted: str
      - coordinates: list of [lon, lat]
      - cumulative_distances: np.ndarray of miles along the polyline from start
    """
    # OSRM expects coordinates in {lon},{lat} format
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{finish_lon},{finish_lat}?overview=full&geometries=geojson"
    headers = {"User-Agent": "FuelOptimizationEngine/1.0"}

    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code != 200:
            raise ValueError(f"OSRM routing API returned HTTP status {response.status_code}")

        data = response.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            msg = data.get("message", "No route found between the specified coordinates")
            raise ValueError(f"Routing failed: {msg}")

        route = data["routes"][0]
        distance_meters = float(route["distance"])
        distance_miles = distance_meters * 0.000621371
        duration_seconds = float(route["duration"])

        coordinates = route["geometry"]["coordinates"] # List of [lon, lat]
        if not coordinates or len(coordinates) < 2:
            raise ValueError("Route polyline contains insufficient coordinates.")

        # Compute cumulative distances along the route polyline
        coords_arr = np.array(coordinates)
        lons = coords_arr[:, 0]
        lats = coords_arr[:, 1]

        leg_dists = haversine_vectorized(lats[:-1], lons[:-1], lats[1:], lons[1:])
        cumulative_distances = np.insert(np.cumsum(leg_dists), 0, 0.0)

        # Scale polyline cumulative distances slightly to match OSRM's highway road distance
        scale = distance_miles / cumulative_distances[-1] if cumulative_distances[-1] > 0 else 1.0
        cumulative_distances = cumulative_distances * scale

        return {
            "total_distance_miles": round(distance_miles, 2),
            "duration_seconds": round(duration_seconds, 1),
            "duration_formatted": format_duration(duration_seconds),
            "coordinates": coordinates,
            "cumulative_distances": cumulative_distances
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error connecting to OSRM: {e}")
        raise ConnectionError(f"Failed to communicate with routing service: {str(e)}")
