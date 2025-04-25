import math
from datetime import datetime, time, timedelta


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


def filter_listings(all_listings, request):
    """
    Filter listings based on request parameters.

    Args:
        all_listings: Initial queryset of listings
        request: The HTTP request containing filter parameters
        current_datetime: Current datetime for reference

    Returns:
        tuple: (filtered_listings, error_messages, warning_messages)
    """
    error_messages = []
    warning_messages = []

    # Apply price filter
    max_price = request.GET.get("max_price")
    if max_price:
        try:
            max_price_val = float(max_price)
            all_listings = all_listings.filter(rent_per_hour__lte=max_price_val)
        except ValueError:
            pass

    filter_type = request.GET.get("filter_type", "single")

    # Single date/time filter
    if filter_type == "single":
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        start_time = request.GET.get("start_time")
        end_time = request.GET.get("end_time")

        if any([start_date, end_date, start_time, end_time]):
            try:
                user_start_str = f"{start_date} {start_time}"
                user_end_str = f"{end_date} {end_time}"
                user_start_dt = datetime.strptime(user_start_str, "%Y-%m-%d %H:%M")
                user_end_dt = datetime.strptime(user_end_str, "%Y-%m-%d %H:%M")

                filtered = []
                for listing in all_listings:
                    if listing.is_available_for_range(user_start_dt, user_end_dt):
                        filtered.append(listing)
                all_listings = filtered
            except ValueError:
                pass

    # Multiple date/time ranges filter
    elif filter_type == "multiple":
        try:
            interval_count = int(request.GET.get("interval_count", "0"))
        except ValueError:
            interval_count = 0

        intervals = []
        for i in range(1, interval_count + 1):
            s_date = request.GET.get(f"start_date_{i}")
            e_date = request.GET.get(f"end_date_{i}")
            s_time = request.GET.get(f"start_time_{i}")
            e_time = request.GET.get(f"end_time_{i}")
            if s_date and e_date and s_time and e_time:
                try:
                    s_dt = datetime.strptime(f"{s_date} {s_time}", "%Y-%m-%d %H:%M")
                    e_dt = datetime.strptime(f"{e_date} {e_time}", "%Y-%m-%d %H:%M")
                    intervals.append((s_dt, e_dt))
                except ValueError:
                    continue

        if intervals:
            filtered = []
            for listing in all_listings:
                available_for_all = True
                for s_dt, e_dt in intervals:
                    if not listing.is_available_for_range(s_dt, e_dt):
                        available_for_all = False
                        break
                if available_for_all:
                    filtered.append(listing)
            all_listings = filtered

    # Recurring pattern filter
    elif filter_type == "recurring":
        r_start_date = request.GET.get("recurring_start_date")
        r_start_time = request.GET.get("recurring_start_time")
        r_end_time = request.GET.get("recurring_end_time")
        pattern = request.GET.get("recurring_pattern", "daily")
        overnight = request.GET.get("recurring_overnight") == "on"
        continue_with_filter = True

        if r_start_date and r_start_time and r_end_time:
            try:
                intervals = []
                start_date_obj = datetime.strptime(r_start_date, "%Y-%m-%d").date()
                s_time = datetime.strptime(r_start_time, "%H:%M").time()
                e_time = datetime.strptime(r_end_time, "%H:%M").time()

                if s_time >= e_time and not overnight:
                    error_messages.append(
                        "Start time must be before end time unless overnight booking is selected"
                    )
                    continue_with_filter = False

                if pattern == "daily":
                    r_end_date = request.GET.get("recurring_end_date")
                    if not r_end_date:
                        error_messages.append(
                            "End date is required for daily recurring pattern"
                        )
                        continue_with_filter = False
                    else:
                        end_date_obj = datetime.strptime(r_end_date, "%Y-%m-%d").date()
                        if end_date_obj < start_date_obj:
                            error_messages.append(
                                "End date must be on or after start date"
                            )
                            continue_with_filter = False
                        else:
                            days_count = (end_date_obj - start_date_obj).days + 1
                            if days_count > 90:
                                warning_messages.append(
                                    "Daily recurring pattern spans over 90 days, results may be limited"
                                )
                            if continue_with_filter:
                                for day_offset in range(days_count):
                                    current_date = start_date_obj + timedelta(
                                        days=day_offset
                                    )
                                    s_dt = datetime.combine(current_date, s_time)
                                    end_date_for_slot = current_date + timedelta(
                                        days=1 if overnight else 0
                                    )
                                    e_dt = datetime.combine(end_date_for_slot, e_time)
                                    intervals.append((s_dt, e_dt))

                elif pattern == "weekly":
                    try:
                        weeks_str = request.GET.get("recurring_weeks")
                        if not weeks_str:
                            error_messages.append(
                                "Number of weeks is required for weekly recurring pattern"
                            )
                            continue_with_filter = False
                        else:
                            weeks = int(weeks_str)
                            if weeks <= 0:
                                error_messages.append(
                                    "Number of weeks must be positive"
                                )
                                continue_with_filter = False
                            elif weeks > 52:
                                warning_messages.append(
                                    "Weekly recurring pattern spans over 52 weeks, results may be limited"
                                )
                            if continue_with_filter:
                                for week_offset in range(weeks):
                                    current_date = start_date_obj + timedelta(
                                        weeks=week_offset
                                    )
                                    s_dt = datetime.combine(current_date, s_time)
                                    end_date_for_slot = current_date + timedelta(
                                        days=1 if overnight else 0
                                    )
                                    e_dt = datetime.combine(end_date_for_slot, e_time)
                                    intervals.append((s_dt, e_dt))
                    except ValueError:
                        error_messages.append("Invalid number of weeks")
                        continue_with_filter = False

                if continue_with_filter and intervals:
                    filtered = []
                    for listing in all_listings:
                        available_for_all = True
                        for s_dt, e_dt in intervals:
                            if overnight and s_time >= e_time:
                                evening_available = listing.is_available_for_range(
                                    s_dt, datetime.combine(s_dt.date(), time(23, 59))
                                )
                                morning_available = listing.is_available_for_range(
                                    datetime.combine(e_dt.date(), time(0, 0)), e_dt
                                )
                                if not (evening_available and morning_available):
                                    available_for_all = False
                                    break
                            elif not listing.is_available_for_range(s_dt, e_dt):
                                available_for_all = False
                                break
                        if available_for_all:
                            filtered.append(listing)
                    all_listings = filtered
            except ValueError:
                error_messages.append("Invalid date or time format")

            if not continue_with_filter:
                from django.db.models import QuerySet

                if isinstance(all_listings, QuerySet):
                    all_listings = all_listings.none()
                else:
                    all_listings = []

    # Apply EV charger filters
    if request.GET.get("has_ev_charger") == "on":
        all_listings = all_listings.filter(has_ev_charger=True)

        # Apply additional EV filters only if has_ev_charger is selected
        charger_level = request.GET.get("charger_level")
        if charger_level:
            all_listings = all_listings.filter(charger_level=charger_level)

        connector_type = request.GET.get("connector_type")
        if connector_type:
            all_listings = all_listings.filter(connector_type=connector_type)

    # Add filter for parking spot size
    if "parking_spot_size" in request.GET and request.GET["parking_spot_size"]:
        all_listings = all_listings.filter(
            parking_spot_size=request.GET["parking_spot_size"]
        )

    # Apply location-based filtering
    processed_listings = []
    search_lat = request.GET.get("lat")
    search_lng = request.GET.get("lng")
    radius = request.GET.get("radius")

    if search_lat and search_lng:
        try:
            search_lat = float(search_lat)
            search_lng = float(search_lng)

            for listing in all_listings:
                try:
                    distance = calculate_distance(
                        search_lat, search_lng, listing.latitude, listing.longitude
                    )
                    listing.distance = distance
                    if radius:
                        radius = float(radius)
                        if distance <= radius:
                            processed_listings.append(listing)
                    else:
                        processed_listings.append(listing)
                except ValueError:
                    listing.distance = None
                    processed_listings.append(listing)
        except ValueError:
            error_messages.append("Invalid coordinates provided")
            processed_listings = list(all_listings)
    else:
        for listing in all_listings:
            listing.distance = None
            processed_listings.append(listing)

    # Sort by distance if location search was applied
    if search_lat and search_lng:
        processed_listings.sort(
            key=lambda x: x.distance if x.distance is not None else float("inf")
        )

    return processed_listings, error_messages, warning_messages
