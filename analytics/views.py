import random
from django.http import JsonResponse


# Create your views here.
def get_traffic_data(request):
    # Define traffic hotspots
    traffic_hotspots = [
        # Manhattan
        {"center": [40.7589, -73.9851], "intensity": 0.8},  # Times Square
        {"center": [40.7527, -73.9772], "intensity": 0.6},  # Grand Central
        {"center": [40.7505, -73.9934], "intensity": 0.7},  # Penn Station
        {"center": [40.7527, -74.0027], "intensity": 0.5},  # Chelsea
        # Brooklyn
        {"center": [40.6922, -73.9875], "intensity": 0.5},  # Downtown Brooklyn
        {"center": [40.6782, -73.9442], "intensity": 0.4},  # Crown Heights
        {"center": [40.7064, -73.9239], "intensity": 0.5},  # Williamsburg
        # Queens
        {"center": [40.7505, -73.9021], "intensity": 0.4},  # Long Island City
        {"center": [40.7429, -73.8489], "intensity": 0.3},  # Jackson Heights
    ]

    traffic_points = []

    # Generate points around each hotspot
    for hotspot in traffic_hotspots:
        # Fewer points (50 instead of 100) for each intensity level
        num_points = int(hotspot["intensity"] * 50)

        for _ in range(num_points):
            # Reduced spread (-0.005 to 0.005 degrees instead of -0.01 to 0.01)
            lat = hotspot["center"][0] + (random.random() - 0.5) * 0.01
            lng = hotspot["center"][1] + (random.random() - 0.5) * 0.01
            # Slightly reduced intensity values
            traffic_points.append([lat, lng, hotspot["intensity"] * 0.8])

    return JsonResponse({"data": traffic_points})
