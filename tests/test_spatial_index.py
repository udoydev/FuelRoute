import numpy as np
from django.test import TestCase
from fuel_routing.services.spatial_index import FuelStationSpatialIndex


class SpatialIndexTests(TestCase):

    def test_spatial_index_loads_stations(self):
        index = FuelStationSpatialIndex.get_instance()
        self.assertGreater(len(index.stations), 5000)
        self.assertIsNotNone(index.tree)

    def test_spatial_index_corridor_query(self):
        index = FuelStationSpatialIndex.get_instance()
        route_coords = [
            [-97.7431, 30.2672], # Austin
            [-97.3400, 31.0900], # Temple
            [-97.1400, 31.5400], # Waco
            [-96.7970, 32.7767]  # Dallas
        ]
        cum_dists = np.array([0.0, 65.0, 105.0, 195.0])

        candidates = index.find_candidate_stations(route_coords, cum_dists, corridor_radius_miles=15.0)
        self.assertGreater(len(candidates), 0)

        for s in candidates:
            self.assertGreaterEqual(s["distance_along_route"], 0.0)
            self.assertLessEqual(s["distance_along_route"], 195.0)
            self.assertGreater(s["retail_price"], 0)
            self.assertIn("lat", s)
            self.assertIn("lon", s)
