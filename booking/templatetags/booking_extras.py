from django import template
import re

register = template.Library()


@register.filter
def format_location(value):
    """
    Extracts the main address from a location string that includes coordinates.
    Example input:
        "383, Grand Street, Lower East Side, Manhattan Community Board 3, Manhattan,
        New York County, New York, 10002, United States"
    Example output: "383 Grand Street, Lower East Side, New York, NY 10002"
    """
    if not value:
        return ""

    # Remove the coordinates part [xx.xxx, yy.yyy]
    location = re.sub(r"\s*\[\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\]\s*$", "", value)

    # Split the remaining string by commas
    parts = [part.strip() for part in location.split(",")]

    # Initialize components
    street_number = ""
    street_name = ""
    neighborhood = ""
    zipcode = ""

    # Process each part
    for part in parts:
        part = part.strip()
        # Skip unwanted parts
        if part in ["United States", "Manhattan", "New York County", "New York"]:
            continue
        if "Community Board" in part:
            continue

        # Extract zip code
        if part.isdigit() and len(part) == 5:
            zipcode = part
            continue

        # Extract street number
        if part.isdigit():
            street_number = part
            continue

        # Extract neighborhood
        if any(
            n in part
            for n in [
                "Lower East Side",
                "Financial District",
                "Upper East Side",
                "Upper West Side",
            ]
        ):
            neighborhood = part
            continue

        # If part contains 'Street', 'Avenue', 'St', 'Ave', etc., it's likely the street name
        if any(
            s in part
            for s in [
                "Street",
                "Avenue",
                "St",
                "Ave",
                "Road",
                "Rd",
                "Boulevard",
                "Blvd",
            ]
        ):
            street_name = part
            continue

    # Build the formatted address
    formatted_parts = []

    # Add street address
    if street_number and street_name:
        formatted_parts.append(f"{street_number} {street_name}")
    elif street_name:
        formatted_parts.append(street_name)

    # Add neighborhood
    if neighborhood:
        formatted_parts.append(neighborhood)

    # Add city and state
    formatted_parts.append("New York")
    formatted_parts.append("NY")

    # Add zip code
    if zipcode:
        formatted_parts[-1] = f"NY {zipcode}"

    # Join the parts back together
    return ", ".join(formatted_parts)
