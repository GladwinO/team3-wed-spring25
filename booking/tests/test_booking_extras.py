from django.test import TestCase
from booking.templatetags.booking_extras import format_location


class FormatLocationTests(TestCase):
    def test_empty_value(self):
        """An empty string should return an empty string."""
        self.assertEqual(format_location(""), "")

    def test_sample_location(self):
        """
        Given a full location string with extra parts,
        expect a formatted address as described in the docstring.
        """
        input_str = (
            "383, Grand Street, Lower East Side, Manhattan Community Board 3, "
            "Manhattan, New York County, New York, 10002, United States"
        )
        expected = "383 Grand Street, Lower East Side, New York, NY 10002"
        self.assertEqual(format_location(input_str), expected)

    def test_location_with_coordinates(self):
        """
        Coordinates at the end of the string should be removed.
        """
        input_str = (
            "123, Example Road, Upper West Side, New York, 10003, United States "
            "[40.7128, -74.0060]"
        )
        expected = "123 Example Road, Upper West Side, New York, NY 10003"
        self.assertEqual(format_location(input_str), expected)

    def test_location_without_number_and_street(self):
        """
        If no street number or street name is found, only city and state remain.
        """
        input_str = "Central Park, New York, United States"
        expected = "New York, NY"
        self.assertEqual(format_location(input_str), expected)

    def test_location_with_no_zipcode(self):
        """
        When a zipcode isn’t present and the street name isn’t detected (because it lacks key words),
        the result should include the neighborhood (if detected) and then city and state.
        """
        input_str = (
            "456, Broadway, Financial District, Manhattan, New York, United States"
        )
        # In this case:
        # "456" is captured as street_number,
        # "Broadway" is not detected as a street name (since it doesn’t contain any of the key words),
        # "Financial District" is captured as the neighborhood,
        # and "Manhattan", "New York", "United States" are skipped.
        # With no street address, the formatted output will include the neighborhood and then "New York, NY".
        expected = "Financial District, New York, NY"
        self.assertEqual(format_location(input_str), expected)
