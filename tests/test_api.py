import json
from django.test import TestCase, Client


class RouteAPITests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_api_route_post_success(self):
        payload = {"start": "Austin, TX", "finish": "Nashville, TN"}
        response = self.client.post("/api/route/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "success")

        summary = data["route_summary"]
        self.assertGreater(summary["total_distance_miles"], 800.0)
        self.assertGreater(summary["total_fuel_cost"], 0)
        self.assertGreater(summary["total_gallons_consumed"], 80.0)
        self.assertEqual(summary["vehicle_mpg"], 10.0)
        self.assertEqual(summary["vehicle_max_range_miles"], 500.0)

        self.assertGreaterEqual(len(data["fuel_stops"]), 1)
        for stop in data["fuel_stops"]:
            self.assertIn("name", stop)
            self.assertIn("retail_price_per_gallon", stop)
            self.assertIn("gallons_purchased", stop)
            self.assertIn("cost_at_stop", stop)
            self.assertEqual(len(stop["coordinates"]), 2)

        geojson = data["map_geojson"]
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertGreaterEqual(len(geojson["features"]), 3)

    def test_api_route_get_success(self):
        response = self.client.get("/api/route/?start=Austin,%20TX&finish=San%20Antonio,%20TX")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertLess(data["route_summary"]["total_distance_miles"], 150.0)

    def test_api_missing_inputs(self):
        response = self.client.post("/api/route/", data=json.dumps({"start": ""}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_api_identical_locations(self):
        payload = {"start": "Austin, TX", "finish": "Austin, TX"}
        response = self.client.post("/api/route/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_map_view_renders_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"FuelRoute - Optimal US Highway Fuel Routing", response.content)
        self.assertIn(b"id=\"map\"", response.content)
