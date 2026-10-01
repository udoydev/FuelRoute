from django.test import TestCase
from fuel_routing.services.fuel_optimizer import optimize_fuel_stops


class FuelOptimizerTests(TestCase):

    def test_short_trip_no_stops_needed(self):
        """Trips under 500 miles require 0 stops if starting with a full tank."""
        candidates = [
            {"distance_along_route": 50.0, "retail_price": 3.00, "name": "Stop A", "opis_id": 1, "address": "123 Main", "city": "CityA", "state": "TX", "lat": 30.0, "lon": -97.0},
            {"distance_along_route": 100.0, "retail_price": 2.80, "name": "Stop B", "opis_id": 2, "address": "456 Oak", "city": "CityB", "state": "TX", "lat": 31.0, "lon": -97.0},
        ]
        stops, cost, gallons = optimize_fuel_stops(200.0, candidates, max_range_miles=500.0, mpg=10.0)
        self.assertEqual(len(stops), 0)
        self.assertEqual(gallons, 20.0)
        self.assertEqual(cost, 56.0)

    def test_medium_trip_requires_one_stop(self):
        """An 800-mile trip requires at least 1 stop to avoid running out of fuel."""
        candidates = [
            {"distance_along_route": 100.0, "retail_price": 3.50, "name": "Stop A", "opis_id": 1, "address": "123 Main", "city": "A", "state": "TX", "lat": 30.0, "lon": -97.0},
            {"distance_along_route": 400.0, "retail_price": 2.90, "name": "Stop B", "opis_id": 2, "address": "456 Oak", "city": "B", "state": "AR", "lat": 34.0, "lon": -92.0},
            {"distance_along_route": 450.0, "retail_price": 2.85, "name": "Stop C", "opis_id": 3, "address": "789 Pine", "city": "C", "state": "AR", "lat": 34.5, "lon": -91.0},
            {"distance_along_route": 750.0, "retail_price": 3.60, "name": "Stop D", "opis_id": 4, "address": "101 Elm", "city": "D", "state": "TN", "lat": 36.0, "lon": -87.0},
        ]
        stops, cost, gallons = optimize_fuel_stops(800.0, candidates, max_range_miles=500.0, mpg=10.0)
        self.assertGreaterEqual(len(stops), 1)
        self.assertEqual(gallons, 80.0)
        self.assertLessEqual(stops[0]["distance_from_start_miles"], 500.0)
        self.assertLessEqual(800.0 - stops[-1]["distance_from_start_miles"], 500.0)
        for s in stops:
            self.assertLessEqual(s["gallons_purchased"], 50.0)

    def test_long_trip_multi_stops(self):
        """A 2,500-mile trip requires multiple stops with no gap exceeding 500 miles."""
        candidates = []
        for d in range(100, 2400, 100):
            candidates.append({
                "distance_along_route": float(d),
                "retail_price": 2.90 + (d % 30) * 0.01,
                "name": f"Stop {d}",
                "opis_id": d,
                "address": f"{d} Hwy",
                "city": "Sample",
                "state": "US",
                "lat": 35.0,
                "lon": -90.0
            })

        stops, cost, gallons = optimize_fuel_stops(2500.0, candidates, max_range_miles=500.0, mpg=10.0)
        self.assertGreaterEqual(len(stops), 4)
        self.assertEqual(gallons, 250.0)

        prev_d = 0.0
        for s in stops:
            gap = s["distance_from_start_miles"] - prev_d
            self.assertLessEqual(gap, 500.0)
            self.assertLessEqual(s["gallons_purchased"], 50.0)
            prev_d = s["distance_from_start_miles"]

        final_gap = 2500.0 - prev_d
        self.assertLessEqual(final_gap, 500.0)

    def test_unreachable_gap_raises_error(self):
        """If there are no stations within 500 miles, a ValueError is raised."""
        candidates = [
            {"distance_along_route": 100.0, "retail_price": 3.00, "name": "Stop 1", "opis_id": 1, "address": "A", "city": "A", "state": "TX", "lat": 30.0, "lon": -97.0},
            {"distance_along_route": 900.0, "retail_price": 3.00, "name": "Stop 2", "opis_id": 2, "address": "B", "city": "B", "state": "TX", "lat": 31.0, "lon": -97.0},
        ]
        with self.assertRaises(ValueError):
            optimize_fuel_stops(1200.0, candidates, max_range_miles=500.0, mpg=10.0)
