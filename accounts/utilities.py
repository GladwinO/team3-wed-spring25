import json
import random

from shapely.geometry import Point, shape


def get_valid_nyc_coordinate():
    """
    Reads a GeoJSON file of NYC land boundaries and generates a random latitude
    and longitude that falls within a land polygon.
    """

    geojson_path = "data/community-districts-polygon.geojson"
    # Load GeoJSON file
    with open(geojson_path, "r") as file:
        geojson_data = json.load(file)

    # Extract polygons from the GeoJSON file
    polygons = [shape(feature["geometry"]) for feature in geojson_data["features"]]

    # Define NYC bounding box (approximate limits to sample within)
    NYC_BOUNDS = {
        "min_lat": 40.477399,  # Southernmost point of NYC
        "max_lat": 40.917577,  # Northernmost point of NYC
        "min_lng": -74.259090,  # Westernmost point of NYC
        "max_lng": -73.700272,  # Easternmost point of NYC
    }

    # Generate a valid coordinate within NYC land boundaries
    while True:
        latitude = random.uniform(NYC_BOUNDS["min_lat"], NYC_BOUNDS["max_lat"])
        longitude = random.uniform(NYC_BOUNDS["min_lng"], NYC_BOUNDS["max_lng"])
        point = Point(longitude, latitude)

        # Ensure the point is inside at least one NYC land polygon
        if any(polygon.contains(point) for polygon in polygons):
            return latitude, longitude  # Return a valid coordinate
