import logging
import requests
import numpy as np
from typing import Dict, Any, List, Tuple
from django.conf import settings

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


def fetch_route_ors(start_lat: float, start_lon: float, finish_lat: float, finish_lon: float, api_key: str) -> Dict[str, Any]:
    """
    Fetches the driving route using OpenRouteService (ORS) API in exactly ONE HTTP call.
    Uses the user's OpenRouteService token in the Authorization header.
    """
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": api_key,
        "Accept": "application/json, application/geo+json",
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [[start_lon, start_lat], [finish_lon, finish_lat]]
    }

    response = requests.post(url, json=body, headers=headers, timeout=14)
    if response.status_code != 200:
        raise ValueError(f"OpenRouteService returned status {response.status_code}: {response.text[:200]}")

    data = response.json()
    features = data.get("features", [])
    if not features:
        raise ValueError("No route returned from OpenRouteService")

    feature = features[0]
    summary = feature.get("properties", {}).get("summary", {})
    distance_meters = float(summary.get("distance", 0))
    distance_miles = distance_meters * 0.000621371
    duration_seconds = float(summary.get("duration", 0))

    coordinates = feature.get("geometry", {}).get("coordinates", [])
    if not coordinates or len(coordinates) < 2:
        raise ValueError("OpenRouteService returned insufficient coordinates.")

    coords_arr = np.array(coordinates)
    lons = coords_arr[:, 0]
    lats = coords_arr[:, 1]

    leg_dists = haversine_vectorized(lats[:-1], lons[:-1], lats[1:], lons[1:])
    cumulative_distances = np.insert(np.cumsum(leg_dists), 0, 0.0)

    scale = distance_miles / cumulative_distances[-1] if cumulative_distances[-1] > 0 else 1.0
    cumulative_distances = cumulative_distances * scale

    return {
        "provider": "OpenRouteService",
        "total_distance_miles": round(distance_miles, 2),
        "duration_seconds": round(duration_seconds, 1),
        "duration_formatted": format_duration(duration_seconds),
        "coordinates": coordinates,
        "cumulative_distances": cumulative_distances
    }


def fetch_route_osrm(start_lat: float, start_lon: float, finish_lat: float, finish_lon: float) -> Dict[str, Any]:
    """
    Fetches the driving route between two points using OSRM in exactly ONE HTTP call.
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{finish_lon},{finish_lat}?overview=full&geometries=geojson"
    headers = {"User-Agent": "FuelOptimizationEngine/1.0"}

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

    coordinates = route["geometry"]["coordinates"]
    if not coordinates or len(coordinates) < 2:
        raise ValueError("Route polyline contains insufficient coordinates.")

    coords_arr = np.array(coordinates)
    lons = coords_arr[:, 0]
    lats = coords_arr[:, 1]

    leg_dists = haversine_vectorized(lats[:-1], lons[:-1], lats[1:], lons[1:])
    cumulative_distances = np.insert(np.cumsum(leg_dists), 0, 0.0)

    scale = distance_miles / cumulative_distances[-1] if cumulative_distances[-1] > 0 else 1.0
    cumulative_distances = cumulative_distances * scale

    return {
        "provider": "OSRM",
        "total_distance_miles": round(distance_miles, 2),
        "duration_seconds": round(duration_seconds, 1),
        "duration_formatted": format_duration(duration_seconds),
        "coordinates": coordinates,
        "cumulative_distances": cumulative_distances
    }


def fetch_driving_route(start_lat: float, start_lon: float, finish_lat: float, finish_lon: float) -> Dict[str, Any]:
    """
    Primary routing entrypoint:
      1. Tries OpenRouteService using the provided OPENROUTESERVICE_API_KEY.
      2. If ORS encounters an error/rate limit, seamlessly falls back to OSRM.
      3. Performs exactly ONE HTTP call.
    """
    ors_key = getattr(settings, "OPENROUTESERVICE_API_KEY", None)

    if ors_key:
        try:
            logger.info("Requesting route from OpenRouteService using configured API key...")
            return fetch_route_ors(start_lat, start_lon, finish_lat, finish_lon, ors_key)
        except Exception as e:
            logger.warning(f"OpenRouteService failed ({e}). Falling back to OSRM...")

    logger.info("Requesting route from OSRM...")
    return fetch_route_osrm(start_lat, start_lon, finish_lat, finish_lon)
