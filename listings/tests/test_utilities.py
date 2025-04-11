from django.test import TestCase

from ..utils import simplify_location


class SimplifyLocationTests(TestCase):
    def test_empty_string(self):
        """An empty location string should return an empty string."""
        self.assertEqual(simplify_location(""), "")

    def test_single_part(self):
        """A location string without a comma should be returned as-is."""
        self.assertEqual(simplify_location("Central Park"), "Central Park")

    def test_exact_two_parts_with_known_city(self):
        """
        For a location string with exactly two parts where the second part
        is a known city, the function returns "building, street, city".
        In this case, both street and city are the same.
        """
        input_str = "Empire State Building, Manhattan"
        # building = "Empire State Building", street = "Manhattan", and since "Manhattan" is in the list,
        # city will be "Manhattan". Expected result is "Empire State Building, Manhattan, Manhattan".
        expected = "Empire State Building, Manhattan, Manhattan"
        self.assertEqual(simplify_location(input_str), expected)

    def test_non_institution_no_known_city(self):
        """
        For a non-educational address without any part matching a known city,
        the default city "New York" is used.
        """
        input_str = "123 Main St, Suite 100, Some Suburb"
        # building = "123 Main St", street = "Suite 100", city defaults to "New York"
        expected = "123 Main St, Suite 100, New York"
        self.assertEqual(simplify_location(input_str), expected)

    def test_with_coordinates(self):
        """
        Coordinates (inside square brackets) are stripped out before processing.
        """
        input_str = "123 Main St, Suite 100, Some Suburb [40.123, -73.456]"
        expected = "123 Main St, Suite 100, New York"
        self.assertEqual(simplify_location(input_str), expected)

    def test_educational_institution(self):
        """
        For educational institutions, only the building and the city are returned.
        """
        input_str = "Tandon School of Engineering, Johnson Street, Downtown Brooklyn, Manhattan, New York"
        # parts: ["Tandon School of Engineering", "Johnson Street", "Downtown Brooklyn", "Manhattan", "New York"]
        # The generator will find "Manhattan" in parts (the first match in the known list).
        expected = "Tandon School of Engineering, Manhattan"
        self.assertEqual(simplify_location(input_str), expected)

    def test_extra_spaces(self):
        """
        Extra spaces should be stripped.
        """
        input_str = "  456 Elm St  ,   Queens  , Extra Info "
        # parts become: ["456 Elm St", "Queens", "Extra Info"]
        # building = "456 Elm St", street = "Queens", and since "Queens" is a known city,
        # expected = "456 Elm St, Queens, Queens"
        expected = "456 Elm St, Queens, Queens"
        self.assertEqual(simplify_location(input_str), expected)
