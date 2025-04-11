import math
from datetime import datetime


def is_booking_slot_covered(booking_slot, intervals):
    """
    Check if the given booking slot is completely covered by at least one interval.

    :param booking_slot: A booking slot instance with attributes start_date, start_time, end_date, end_time.
    :param intervals: A list of tuples (start_dt, end_dt) where each is a datetime object.
    :return: True if the booking slot is fully within one of the intervals, otherwise False.
    """
    booking_start = datetime.combine(booking_slot.start_date, booking_slot.start_time)
    booking_end = datetime.combine(booking_slot.end_date, booking_slot.end_time)

    for iv_start, iv_end in intervals:
        if iv_start <= booking_start and iv_end >= booking_end:
            return True
    return False


def is_booking_covered_by_intervals(booking, intervals):
    """
    Check if every slot in the booking is completely covered by one of the intervals.

    :param booking: A booking instance with related slots accessible via booking.slots.all()
    :param intervals: A list of tuples (start_dt, end_dt) representing new availability intervals.
    :return: True if all booking slots are fully covered, otherwise False.
    """
    for slot in booking.slots.all():
        if not is_booking_slot_covered(slot, intervals):
            return False
    return True


def simplify_location(location_string):
    """
    Simplifies a location string.
    Example: "Tandon School of Engineering, Johnson Street, Downtown Brooklyn, Brooklyn..."
    becomes "Tandon School of Engineering, Brooklyn"

    Args:
        location_string (str): Full location string that may include coordinates

    Returns:
        str: Simplified location name
    """
    # Extract location name part before coordinates
    location_full = location_string.split("[")[0].strip()
    if not location_full:
        return ""

    parts = [part.strip() for part in location_full.split(",")]
    if len(parts) < 2:
        return location_full

    building = parts[0]
    city = next(
        (
            part
            for part in parts
            if part.strip()
            in ["Brooklyn", "Manhattan", "Queens", "Bronx", "Staten Island"]
        ),
        "New York",
    )

    # Handle educational institutions differently
    if any(
        term in building.lower()
        for term in ["school", "university", "college", "institute"]
    ):
        return f"{building}, {city}"

    street = parts[1]
    return f"{building}, {street}, {city}"


def calculate_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the Haversine distance between two points on the earth.

    Args:
        lat1, lng1: Latitude and longitude of first point
        lat2, lng2: Latitude and longitude of second point

    Returns:
        Distance in kilometers, rounded to 1 decimal place
    """
    R = 6371  # Earth's radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) * math.sin(dlng / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 1)


def extract_coordinates(location_string):
    """
    Extract latitude and longitude from a location string.

    Args:
        location_string: String containing coordinates in format "name [lat,lng]"

    Returns:
        tuple: (latitude, longitude) as floats

    Raises:
        ValueError: If coordinates cannot be extracted
    """
    try:
        coords = location_string.split("[")[1].strip("]").split(",")
        return float(coords[0]), float(coords[1])
    except (IndexError, ValueError) as e:
        raise ValueError(f"Could not extract coordinates from location string: {e}")


def has_active_filters(request):
    """
    Check if any filters are actively applied (have non-empty values)

    Args:
        request: The HTTP request object

    Returns:
        bool: True if any filter is actively applied, False otherwise
    """
    # Check non-recurring filters first
    non_recurring_filters = [
        "max_price",
        "has_ev_charger",
        "charger_level",
        "connector_type",
    ]

    for param in non_recurring_filters:
        value = request.GET.get(param, "")
        if value and value != "None" and value != "":
            return True

    # Check if single-time filter is active
    if request.GET.get("filter_type") == "single" and any(
        request.GET.get(param)
        for param in ["start_date", "end_date", "start_time", "end_time"]
    ):
        return True

    # Check if all recurring filters are active together
    recurring_filters = [
        "recurring_start_date",
        "recurring_start_time",
        "recurring_end_time",
        "recurring_pattern",
        "recurring_end_date",
        "recurring_weeks",
    ]

    # Only consider recurring filters active if all necessary ones have values
    recurring_values = [request.GET.get(param, "") for param in recurring_filters]
    if all(value and value != "None" and value != "" for value in recurring_values):
        return True

    return False
