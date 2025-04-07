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
