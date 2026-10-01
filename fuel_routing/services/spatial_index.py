import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)

EARTH_RADIUS_MILES = 3958.8


def latlon_to_cartesian(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Converts arrays of latitudes and longitudes (in degrees) to 3D unit sphere cartesian coordinates."""
    lat_r = np.radians(lats)
    lon_r = np.radians(lons)
    x = np.cos(lat_r) * np.cos(lon_r)
    y = np.cos(lat_r) * np.sin(lon_r)
    z = np.sin(lat_r)
    return np.column_stack((x, y, z))


class FuelStationSpatialIndex:
    _instance: Optional["FuelStationSpatialIndex"] = None

    def __init__(self):
        self.stations: List[Dict[str, Any]] = []
        self.tree: Optional[cKDTree] = None
        self._load_and_index()

    @classmethod
    def get_instance(cls) -> "FuelStationSpatialIndex":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_and_index(self):
        """Loads geocoded fuel stations and constructs a 3D spherical cKDTree index."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        json_path = os.path.join(data_dir, "stations_geocoded.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Fuel stations database not found at {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            self.stations = json.load(f)

        if not self.stations:
            raise ValueError("No stations loaded from geocoded fuel database.")

        st_lats = np.array([s["lat"] for s in self.stations], dtype=np.float64)
        st_lons = np.array([s["lon"] for s in self.stations], dtype=np.float64)

        cart_coords = latlon_to_cartesian(st_lats, st_lons)
        self.tree = cKDTree(cart_coords)
        logger.info(f"Loaded and indexed {len(self.stations)} fuel stations into spherical cKDTree.")

    def find_candidate_stations(
        self,
        route_coordinates: List[List[float]],
        cumulative_distances: np.ndarray,
        corridor_radius_miles: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Efficiently finds all fuel stations within `corridor_radius_miles` of the route polyline.
        Assigns each matched station its approximate distance along the route from the start.
        """
        if not self.tree or not self.stations:
            return []

        coords_arr = np.array(route_coordinates, dtype=np.float64)
        r_lons = coords_arr[:, 0]
        r_lats = coords_arr[:, 1]

        route_cart = latlon_to_cartesian(r_lats, r_lons)

        # Great-circle distance converted to chord radius on unit sphere
        theta = corridor_radius_miles / EARTH_RADIUS_MILES
        chord_radius = 2.0 * np.sin(theta / 2.0)

        # Batch query all route points against the KD-Tree
        neighbors = self.tree.query_ball_point(route_cart, r=chord_radius)

        station_to_route_idx: Dict[int, int] = {}
        for r_idx, s_indices in enumerate(neighbors):
            for s_idx in s_indices:
                if s_idx not in station_to_route_idx:
                    station_to_route_idx[s_idx] = r_idx

        candidates: List[Dict[str, Any]] = []
        for s_idx, r_idx in station_to_route_idx.items():
            station_data = dict(self.stations[s_idx])
            station_data["distance_along_route"] = float(cumulative_distances[r_idx])
            candidates.append(station_data)

        # Sort candidate stations by distance along the route
        candidates.sort(key=lambda s: s["distance_along_route"])
        return candidates
