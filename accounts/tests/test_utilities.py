# accounts/tests/test_utilities.py

import json
import unittest
from unittest.mock import mock_open, patch

from shapely.geometry import Point, shape
from accounts.utilities import get_valid_nyc_coordinate


class GetValidNYCCoordinateTest(unittest.TestCase):
    def setUp(self):
        # Create a dummy GeoJSON that covers the entire NYC_BOUNDS defined in the function.
        # This polygon is a rectangle matching the bounding box.
        self.dummy_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-74.259090, 40.477399],
                                [-74.259090, 40.917577],
                                [-73.700272, 40.917577],
                                [-73.700272, 40.477399],
                                [-74.259090, 40.477399],
                            ]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        self.dummy_geojson_str = json.dumps(self.dummy_geojson)

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_invalid_json_raises_exception(self, mock_file):
        """
        Test that if the GeoJSON file contains invalid JSON, a JSONDecodeError is raised.
        """
        with self.assertRaises(json.JSONDecodeError):
            get_valid_nyc_coordinate()

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_valid_coordinate(self, mock_file):
        """
        Test that get_valid_nyc_coordinate returns a coordinate that lies within NYC_BOUNDS
        and is contained in at least one polygon from the dummy GeoJSON.
        """
        # Set the file's read() output to our dummy geojson string
        mock_file.return_value.read.return_value = self.dummy_geojson_str

        # Call the function to get a coordinate
        latitude, longitude = get_valid_nyc_coordinate()

        # NYC_BOUNDS as defined in the function
        min_lat, max_lat = 40.477399, 40.917577
        min_lng, max_lng = -74.259090, -73.700272

        # Verify that the coordinate is within the bounding box
        self.assertGreaterEqual(latitude, min_lat)
        self.assertLessEqual(latitude, max_lat)
        self.assertGreaterEqual(longitude, min_lng)
        self.assertLessEqual(longitude, max_lng)

        # Build a point (remember: shapely's Point expects (lng, lat))
        point = Point(longitude, latitude)

        # Verify that the point is contained in the polygon extracted from our dummy GeoJSON
        polygon = shape(self.dummy_geojson["features"][0]["geometry"])
        self.assertTrue(polygon.contains(point))


if __name__ == "__main__":
    unittest.main()
