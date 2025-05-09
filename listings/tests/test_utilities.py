from ..utils import simplify_location, generate_recurring_listing_slots
from datetime import timedelta, time
import datetime as dt  # Use alias to avoid conflict
from datetime import datetime  # Keep this for class access

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone

from listings.models import Listing, ListingSlot
from listings.utils import filter_listings


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


class RecurringListingSlotsTests(TestCase):
    """Tests for the generate_recurring_listing_slots utility function"""

    def test_daily_pattern(self):
        """Test generating daily recurring slots"""
        # Use dynamic dates based on today
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        end_date = today + timedelta(days=3)  # 3 days from today
        start_time = time(9, 0)
        end_time = time(17, 0)

        slots = generate_recurring_listing_slots(
            start_date=start_date,
            start_time=start_time,
            end_time=end_time,
            pattern="daily",
            end_date=end_date,
        )

        # Should generate 3 slots (for 3 days)
        self.assertEqual(len(slots), 3)

        # Check first slot is tomorrow
        self.assertEqual(slots[0]["start_date"], start_date)
        self.assertEqual(slots[0]["start_time"], start_time)
        self.assertEqual(
            slots[0]["end_date"], start_date
        )  # Same day since not overnight
        self.assertEqual(slots[0]["end_time"], end_time)

        # Check last slot is end_date
        self.assertEqual(slots[2]["start_date"], end_date)
        self.assertEqual(slots[2]["end_time"], end_time)

    def test_daily_pattern_single_day(self):
        """Test daily pattern with start_date = end_date (edge case)"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        start_time = time(9, 0)
        end_time = time(17, 0)

        slots = generate_recurring_listing_slots(
            start_date=start_date,
            start_time=start_time,
            end_time=end_time,
            pattern="daily",
            end_date=start_date,  # Same day
        )

        # Should generate exactly 1 slot
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["start_date"], start_date)
        self.assertEqual(slots[0]["end_date"], start_date)

    def test_weekly_pattern(self):
        """Test generating weekly recurring slots"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        start_time = time(9, 0)
        end_time = time(17, 0)
        weeks = 3

        slots = generate_recurring_listing_slots(
            start_date=start_date,
            start_time=start_time,
            end_time=end_time,
            pattern="weekly",
            weeks=weeks,
        )

        # Should generate 3 slots (for 3 weeks)
        self.assertEqual(len(slots), 3)

        # Check dates are one week apart
        self.assertEqual(slots[0]["start_date"], start_date)
        self.assertEqual(slots[1]["start_date"], start_date + timedelta(weeks=1))
        self.assertEqual(slots[2]["start_date"], start_date + timedelta(weeks=2))

        # Check times are consistent
        for slot in slots:
            self.assertEqual(slot["start_time"], start_time)
            self.assertEqual(slot["end_time"], end_time)

    def test_overnight_daily_pattern(self):
        """Test overnight slots with daily pattern"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        end_date = today + timedelta(days=2)  # Day after tomorrow
        start_time = time(20, 0)  # 8 PM
        end_time = time(8, 0)  # 8 AM

        slots = generate_recurring_listing_slots(
            start_date=start_date,
            start_time=start_time,
            end_time=end_time,
            pattern="daily",
            is_overnight=True,
            end_date=end_date,
        )

        # Should generate 2 slots
        self.assertEqual(len(slots), 2)

        # Check overnight dates (end_date should be day after start_date)
        for slot in slots:
            self.assertEqual(slot["end_date"], slot["start_date"] + timedelta(days=1))

    def test_overnight_weekly_pattern(self):
        """Test overnight slots with weekly pattern"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        start_time = time(20, 0)  # 8 PM
        end_time = time(8, 0)  # 8 AM

        slots = generate_recurring_listing_slots(
            start_date=start_date,
            start_time=start_time,
            end_time=end_time,
            pattern="weekly",
            is_overnight=True,
            weeks=2,
        )

        # Should generate 2 slots (for 2 weeks)
        self.assertEqual(len(slots), 2)

        # Check overnight dates and weekly separation
        self.assertEqual(slots[0]["start_date"], start_date)
        self.assertEqual(slots[0]["end_date"], start_date + timedelta(days=1))
        self.assertEqual(slots[1]["start_date"], start_date + timedelta(weeks=1))
        self.assertEqual(slots[1]["end_date"], start_date + timedelta(weeks=1, days=1))

    def test_missing_end_date_for_daily(self):
        """Test error when end_date is missing for daily pattern"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        start_time = time(9, 0)
        end_time = time(17, 0)

        with self.assertRaises(ValueError) as context:
            generate_recurring_listing_slots(
                start_date=start_date,
                start_time=start_time,
                end_time=end_time,
                pattern="daily",
                # Missing end_date
            )

        self.assertIn("End date is required", str(context.exception))

    def test_missing_weeks_for_weekly(self):
        """Test error when weeks is missing for weekly pattern"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        start_time = time(9, 0)
        end_time = time(17, 0)

        with self.assertRaises(ValueError) as context:
            generate_recurring_listing_slots(
                start_date=start_date,
                start_time=start_time,
                end_time=end_time,
                pattern="weekly",
                # Missing weeks
            )

        self.assertIn("Number of weeks is required", str(context.exception))

    def test_invalid_pattern(self):
        """Test error for invalid pattern"""
        today = timezone.now().date()
        start_date = today + timedelta(days=1)  # Tomorrow
        start_time = time(9, 0)
        end_time = time(17, 0)

        with self.assertRaises(ValueError) as context:
            generate_recurring_listing_slots(
                start_date=start_date,
                start_time=start_time,
                end_time=end_time,
                pattern="monthly",  # Invalid pattern
            )

        self.assertIn("Unknown pattern", str(context.exception))


class FilterListingsTestCase(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password1")
        self.user2 = User.objects.create_user(username="user2", password="password2")

        # Create base listings
        self.listing1 = Listing.objects.create(
            user=self.user1,
            title="Parking Spot Near Central Park",
            location="Central Park [40.7812, -73.9665]",
            rent_per_hour=10.00,
            description="Nice spot near Central Park",
            has_ev_charger=True,
            charger_level="L2",
            connector_type="J1772",
            parking_spot_size="STANDARD",
        )

        self.listing2 = Listing.objects.create(
            user=self.user1,
            title="Affordable Spot in Brooklyn",
            location="Brooklyn [40.6782, -73.9442]",
            rent_per_hour=5.00,
            description="Cheap spot in Brooklyn",
            has_ev_charger=False,
            parking_spot_size="COMPACT",
        )

        self.listing3 = Listing.objects.create(
            user=self.user2,
            title="Premium Manhattan Parking",
            location="Manhattan [40.7831, -73.9712]",
            rent_per_hour=20.00,
            description="Luxury parking in Manhattan",
            has_ev_charger=True,
            charger_level="L3",
            connector_type="TESLA",
            parking_spot_size="OVERSIZE",
        )

        self.listing4 = Listing.objects.create(
            user=self.user2,
            title="Parking Spot Near Brooklyn Bridge",
            location="Brooklyn Bridge [40.7061, -73.9969]",
            rent_per_hour=15.00,
            description="Nice spot near Brooklyn Bridge",
            has_ev_charger=True,
            charger_level="L2",
            connector_type="J1772",
            parking_spot_size="STANDARD",
        )

        # Define dates and times for availability slots
        today = timezone.now().date()
        tomorrow = today + dt.timedelta(days=1)
        next_week = today + dt.timedelta(days=7)

        # Create availability slots

        # Listing 1: Available today 9AM-5PM and tomorrow 10AM-3PM
        ListingSlot.objects.create(
            listing=self.listing1,
            start_date=today,
            start_time=time(9, 0),
            end_date=today,
            end_time=time(17, 0),
        )

        ListingSlot.objects.create(
            listing=self.listing1,
            start_date=tomorrow,
            start_time=time(10, 0),
            end_date=tomorrow,
            end_time=time(15, 0),
        )

        # Listing 2: Available today 12PM-6PM and next week 10AM-8PM
        ListingSlot.objects.create(
            listing=self.listing2,
            start_date=today,
            start_time=time(12, 0),
            end_date=today,
            end_time=time(18, 0),
        )

        ListingSlot.objects.create(
            listing=self.listing2,
            start_date=next_week,
            start_time=time(10, 0),
            end_date=next_week,
            end_time=time(20, 0),
        )

        # Listing 3: Available tomorrow full day
        ListingSlot.objects.create(
            listing=self.listing3,
            start_date=tomorrow,
            start_time=time(0, 0),
            end_date=tomorrow,
            end_time=time(23, 59),
        )

        # Listings 4: Availble tomorrow 10AM until next week 3PM
        ListingSlot.objects.create(
            listing=self.listing4,
            start_date=tomorrow,
            start_time=time(10, 0),
            end_date=next_week,
            end_time=time(15, 0),
        )

        self.factory = RequestFactory()

    def create_mock_request(self, params=None):
        """Create a mock request with the given parameters"""
        if params is None:
            params = {}
        request = self.factory.get("/", params)
        request.GET = params
        return request

    def test_price_filter(self):
        """Test filtering by maximum price"""
        # Test price filter <= 15
        request = self.create_mock_request({"max_price": "15"})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 3)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        # Test price filter <= 5
        request = self.create_mock_request({"max_price": "5"})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing2, filtered_listings)

        # Test invalid price filter
        request = self.create_mock_request({"max_price": "-10"})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertTrue(any("must be positive" in error for error in errors))

    def test_single_date_filter(self):
        """Test filtering by single date"""
        today = timezone.now().date().strftime("%Y-%m-%d")
        tomorrow = (timezone.now().date() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (timezone.now().date() + dt.timedelta(days=7)).strftime("%Y-%m-%d")

        # Test today only
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": today}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)

        # Test tomorrow only
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": tomorrow}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 3)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing3, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        # Test next week only
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": next_week}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing2, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        # Tests for only end day
        request = self.create_mock_request({"filter_type": "single", "end_date": today})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)

        request = self.create_mock_request(
            {"filter_type": "single", "end_date": tomorrow}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 3)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing3, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        request = self.create_mock_request(
            {"filter_type": "single", "end_date": next_week}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing2, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

    def test_single_time_filter(self):
        """Test filtering by single time"""
        # Test morning (9AM)
        request = self.create_mock_request(
            {"filter_type": "single", "start_time": "09:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 3)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing3, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        # Test afternoon (14:00 / 2PM)
        request = self.create_mock_request(
            {"filter_type": "single", "start_time": "14:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(
            len(filtered_listings), 4
        )  # All listings have availability at 2PM on some day

        request = self.create_mock_request(
            {"filter_type": "single", "end_time": "14:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(
            len(filtered_listings), 4
        )  # All listings have availability at 2PM on some day

        # Test morning (4AM) end time
        request = self.create_mock_request(
            {"filter_type": "single", "end_time": "4:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing3, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

    def test_date_range_filter(self):
        """Test filtering by date range"""
        today = timezone.now().date().strftime("%Y-%m-%d")
        tomorrow = (timezone.now().date() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (timezone.now().date() + dt.timedelta(days=7)).strftime("%Y-%m-%d")

        # Test today to tomorrow
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": today, "end_date": tomorrow}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        # None of our listings cover the full range from today to tomorrow
        self.assertEqual(len(filtered_listings), 0)

        # Test today only (start_date = end_date)
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": today, "end_date": today}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)

        # Test tomorrow to next week
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": tomorrow, "end_date": next_week}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing4, filtered_listings)

    def test_ev_charger_filter(self):
        """Test filtering by EV charger options"""
        # Test has_ev_charger
        request = self.create_mock_request({"has_ev_charger": "on"})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 3)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing3, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        # Test charger level
        request = self.create_mock_request(
            {"has_ev_charger": "on", "charger_level": "L3"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing3, filtered_listings)

        # Test connector type
        request = self.create_mock_request(
            {"has_ev_charger": "on", "connector_type": "J1772"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

    def test_parking_size_filter(self):
        """Test filtering by parking spot size"""
        # Test compact spots
        request = self.create_mock_request({"parking_spot_size": "COMPACT"})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing2, filtered_listings)

        # Test standard spots
        request = self.create_mock_request({"parking_spot_size": "STANDARD"})
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

    def test_location_filter(self):
        """Test filtering by location and radius"""
        # Test location filter with radius (near Central Park coordinates)
        request = self.create_mock_request(
            {"lat": "40.7812", "lng": "-73.9665", "radius": "1"}  # 1km radius
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(
            len(filtered_listings), 2
        )  # Listing 1 and 3 should be within 1km

        # Check distance values are set
        self.assertTrue(
            all(hasattr(listing, "distance") for listing in filtered_listings)
        )

        # Test smaller radius
        request = self.create_mock_request(
            {"lat": "40.7812", "lng": "-73.9665", "radius": "0.1"}  # 100m radius
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(
            len(filtered_listings), 1
        )  # Only listing 1 should be within 100m

    def test_multiple_filters(self):
        """Test applying multiple filters together"""
        today = timezone.now().date().strftime("%Y-%m-%d")

        # Test combining date, price, and EV filters
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "max_price": "15",
                "has_ev_charger": "on",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

    def test_multiple_date_ranges(self):
        """Test filtering with multiple date ranges"""
        today = timezone.now().date().strftime("%Y-%m-%d")
        tomorrow = (timezone.now().date() + dt.timedelta(days=1)).strftime("%Y-%m-%d")

        # Set up request with multiple intervals
        request = self.create_mock_request(
            {
                "filter_type": "multiple",
                "interval_count": "2",
                "start_date_1": today,
                "end_date_1": today,
                "start_time_1": "10:00",
                "end_time_1": "15:00",
                "start_date_2": tomorrow,
                "end_date_2": tomorrow,
                "start_time_2": "10:00",
                "end_time_2": "15:00",
            }
        )

        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

    def test_recurring_daily_filter(self):
        """Test filtering with recurring daily pattern"""
        today = timezone.now().date().strftime("%Y-%m-%d")
        two_days_later = (timezone.now().date() + dt.timedelta(days=2)).strftime(
            "%Y-%m-%d"
        )

        # Set up request with recurring daily pattern
        request = self.create_mock_request(
            {
                "filter_type": "recurring",
                "recurring_pattern": "daily",
                "recurring_start_date": today,
                "recurring_end_date": two_days_later,
                "recurring_start_time": "10:00",
                "recurring_end_time": "15:00",
            }
        )

        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        # No listings available for 3 consecutive days from 10-15
        self.assertEqual(len(filtered_listings), 0)

    def test_recurring_weekly_filter(self):
        """Test filtering with recurring weekly pattern"""
        today = timezone.now().date().strftime("%Y-%m-%d")

        # Set up request with recurring weekly pattern for just 1 week
        request = self.create_mock_request(
            {
                "filter_type": "recurring",
                "recurring_pattern": "weekly",
                "recurring_start_date": today,
                "recurring_weeks": "1",
                "recurring_start_time": "10:00",
                "recurring_end_time": "15:00",
            }
        )

        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

    def test_error_handling(self):
        """Test error handling in the filter function"""
        # Test end date before start date
        today = timezone.now().date().strftime("%Y-%m-%d")
        yesterday = (timezone.now().date() - dt.timedelta(days=1)).strftime("%Y-%m-%d")

        request = self.create_mock_request(
            {"filter_type": "single", "start_date": today, "end_date": yesterday}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertTrue(
            any("Start date cannot be after end date" in error for error in errors)
        )

        # Add these tests to the test_error_handling method

    def test_invalid_combinations(self):
        """Test that invalid date/time combinations return appropriate errors"""
        today = timezone.now().date().strftime("%Y-%m-%d")

        # Test Case 1: Start date and end time without end date
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": today, "end_time": "15:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertTrue(
            any(
                "When providing an end time, you must also select an end date" in error
                for error in errors
            )
        )
        self.assertEqual(
            len(filtered_listings), 0
        )  # No listings should be returned for invalid combinations

        # Test Case 2: Start date + start time + end time without end date
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "start_time": "10:00",
                "end_time": "15:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertTrue(
            any(
                "When providing an end time, you must also select an end date" in error
                for error in errors
            )
        )
        self.assertEqual(len(filtered_listings), 0)

        # Test Case 3: End date and start time without start date
        tomorrow = (timezone.now().date() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        request = self.create_mock_request(
            {"filter_type": "single", "end_date": tomorrow, "start_time": "10:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertTrue(
            any(
                "When providing a start time, you must also select a start date"
                in error
                for error in errors
            )
        )
        self.assertEqual(len(filtered_listings), 0)

        # Test Case 4: End date + start time + end time without start date
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "end_date": tomorrow,
                "start_time": "10:00",
                "end_time": "15:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertTrue(
            any(
                "When providing a start time, you must also select a start date"
                in error
                for error in errors
            )
        )
        self.assertEqual(len(filtered_listings), 0)

    def test_date_time_combinations(self):
        """Test all possible date/time filter combinations thoroughly"""
        today = timezone.now().date().strftime("%Y-%m-%d")
        tomorrow = (timezone.now().date() + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (timezone.now().date() + dt.timedelta(days=7)).strftime("%Y-%m-%d")

        # 1. Start date and start time
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": today, "start_time": "10:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

        # 2. End date and end time
        request = self.create_mock_request(
            {"filter_type": "single", "end_date": today, "end_time": "17:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)

        # 3. Start date and end date (different dates)
        request = self.create_mock_request(
            {"filter_type": "single", "start_date": tomorrow, "end_date": next_week}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing4, filtered_listings)

        # 4. Start time and end time
        request = self.create_mock_request(
            {"filter_type": "single", "start_time": "10:00", "end_time": "15:00"}
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        # Should match listings with slots that fully contain this time range
        self.assertEqual(len(filtered_listings), 4)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)
        self.assertIn(self.listing3, filtered_listings)
        self.assertIn(self.listing4, filtered_listings)

        # 5. Start date, end date and start time - same day
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "end_date": today,
                "start_time": "10:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

        # 6. Start date, end date and start time - different days
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": tomorrow,
                "end_date": next_week,
                "start_time": "10:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing4, filtered_listings)

        # 7. Start date, end date and end time - same day
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "end_date": today,
                "end_time": "17:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 2)
        self.assertIn(self.listing1, filtered_listings)
        self.assertIn(self.listing2, filtered_listings)

        # 8. Start date, end date and end time - different days
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "end_date": tomorrow,
                "end_time": "14:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 0)

        # 9. Full date/time range - same day
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "end_date": today,
                "start_time": "10:00",
                "end_time": "15:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

        # 10. Full date/time range - different days
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": tomorrow,
                "end_date": next_week,
                "start_time": "11:00",
                "end_time": "14:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing4, filtered_listings)

        # Test today from 10AM to 3PM
        request = self.create_mock_request(
            {
                "filter_type": "single",
                "start_date": today,
                "end_date": today,
                "start_time": "10:00",
                "end_time": "15:00",
            }
        )
        filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), request
        )
        self.assertEqual(len(filtered_listings), 1)
        self.assertIn(self.listing1, filtered_listings)

    def test_pagination_with_filters(self):
        """Test that filters are preserved when paginating through results"""
        # Create additional listings to have more than one page
        # We already have 4 listings, so let's add 8 more to cross the 10-item pagination threshold

        # Common dates for new listings
        today = timezone.now().date()

        # Create 8 additional listings - 4 with EV chargers (expensive) and 4 without (cheaper)
        for i in range(8):
            has_ev = i < 4  # First 4 have EV chargers
            price = 25.00 if has_ev else 7.50  # EV spots cost more

            listing = Listing.objects.create(
                user=self.user1,
                title=f"Additional Listing {i+1}",
                location=f"Location {i+1} [40.7, -74.0]",
                rent_per_hour=price,
                description=f"Additional listing {i+1}",
                has_ev_charger=has_ev,
                charger_level="L2" if has_ev else "",  # Empty string instead of None
                connector_type=(
                    "J1772" if has_ev else ""
                ),  # Empty string instead of None
                parking_spot_size="STANDARD",
            )

            # Create availability slot for today
            ListingSlot.objects.create(
                listing=listing,
                start_date=today,
                start_time=time(10, 0),
                end_date=today,
                end_time=time(18, 0),
            )

        # Now we should have 12 total listings

        # Apply a filter for EV chargers
        mock_request = self.create_mock_request({"has_ev_charger": "on"})

        # Get all filtered listings
        all_filtered_listings, errors, warnings = filter_listings(
            Listing.objects.all(), mock_request
        )

        # We should have 7 listings with EV chargers
        # (self.listing1, self.listing3, self.listing4 from setUp + 4 new ones)
        self.assertEqual(len(all_filtered_listings), 7)

        # Check that all results have EV chargers
        for listing in all_filtered_listings:
            self.assertTrue(listing.has_ev_charger)

        # Manually simulate pagination - split into pages of 5 items
        page_size = 5
        page1 = all_filtered_listings[:page_size]
        page2 = all_filtered_listings[page_size:]

        # Check both pages contain only listings with EV chargers
        for listing in page1:
            self.assertTrue(listing.has_ev_charger)

        for listing in page2:
            self.assertTrue(listing.has_ev_charger)

        # Make sure we got different listings on different pages
        page1_ids = {listing.id for listing in page1}
        page2_ids = {listing.id for listing in page2}
        self.assertEqual(len(page1_ids.intersection(page2_ids)), 0)  # No overlap
