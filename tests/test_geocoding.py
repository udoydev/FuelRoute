from django.test import TestCase
from fuel_routing.services.geocoding import geocode_location


class GeocodingTests(TestCase):

    def test_coordinate_parsing(self):
        lat, lon, name = geocode_location("30.2672, -97.7431")
        self.assertEqual(round(lat, 4), 30.2672)
        self.assertEqual(round(lon, 4), -97.7431)
        self.assertIn("Coordinates", name)

    def test_common_city_lookup(self):
        lat, lon, name = geocode_location("Austin, TX")
        self.assertEqual(round(lat, 2), 30.27)
        self.assertEqual(round(lon, 2), -97.74)
        self.assertIn("Austin", name)

    def test_invalid_location_raises(self):
        with self.assertRaises(ValueError):
            geocode_location("NonExistentCityXYZ123456789")
