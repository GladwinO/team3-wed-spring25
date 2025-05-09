from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User

from listings.forms import (
    ListingForm,
    ListingSlotForm,
    validate_non_overlapping_slots,
    ReviewForm,
    RecurringListingForm,
)
from listings.models import Listing


class ListingFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="formuser", password="pass")
        self.valid_data = {
            "title": "Test Listing",
            "location": "123, Main Street, City, State, 12345, Country",
            "rent_per_hour": "10.00",
            "description": "A test listing",
            "has_ev_charger": False,
            "charger_level": "L2",
            "connector_type": "J1772",
            "parking_spot_size": "STANDARD",
        }

    def test_new_listing_form_valid(self):
        form = ListingForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        cleaned = form.clean()
        # When has_ev_charger is False, the EV fields should be cleared.
        self.assertEqual(cleaned.get("charger_level"), "")
        self.assertEqual(cleaned.get("connector_type"), "")

    def test_existing_listing_location_disabled(self):
        # Create a listing using valid_data (has_ev_charger is already in valid_data)
        listing = Listing.objects.create(user=self.user, **self.valid_data)
        form = ListingForm(instance=listing)
        self.assertTrue(form.fields["location"].disabled)

    def test_ev_charger_required_when_enabled(self):
        data = self.valid_data.copy()
        data["has_ev_charger"] = True
        data["charger_level"] = ""
        data["connector_type"] = ""
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("charger_level", form.errors)
        self.assertIn("connector_type", form.errors)

    def test_save_clears_ev_fields_when_disabled(self):
        data = self.valid_data.copy()
        data["has_ev_charger"] = False
        data["charger_level"] = "L2"
        data["connector_type"] = "J1772"
        form = ListingForm(data=data)
        self.assertTrue(form.is_valid())
        # Save with commit=False so we can assign the required user.
        listing = form.save(commit=False)
        listing.user = self.user
        listing.save()
        self.assertEqual(listing.charger_level, "")
        self.assertEqual(listing.connector_type, "")

    def test_valid_parking_spot_sizes(self):
        """Test that different valid parking spot sizes are accepted"""
        valid_sizes = ["STANDARD", "COMPACT", "OVERSIZE", "COMMERCIAL"]

        for size in valid_sizes:
            data = self.valid_data.copy()
            data["parking_spot_size"] = size
            form = ListingForm(data=data)
            self.assertTrue(form.is_valid(), f"Form should be valid with size {size}")

    def test_invalid_parking_spot_size(self):
        """Test that invalid parking spot sizes are rejected"""
        data = self.valid_data.copy()
        data["parking_spot_size"] = "INVALID_SIZE"
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("parking_spot_size", form.errors)

    def test_negative_rent_rate(self):
        """Test that negative rent rates are rejected"""
        data = self.valid_data.copy()
        data["rent_per_hour"] = "-10.00"
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("rent_per_hour", form.errors)
        self.assertIn("Price must be greater than zero", form.errors["rent_per_hour"])

    def test_zero_rent_rate(self):
        """Test that zero rent rates are rejected"""
        data = self.valid_data.copy()
        data["rent_per_hour"] = "0.00"
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("rent_per_hour", form.errors)
        self.assertIn("Price must be greater than zero", form.errors["rent_per_hour"])

    def test_no_title(self):
        """Test that missing title is rejected"""
        data = self.valid_data.copy()
        data["title"] = ""
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("Please enter a spot title", form.errors["title"])

    def test_no_description(self):
        """Test that missing description is rejected"""
        data = self.valid_data.copy()
        data["description"] = ""
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)
        self.assertIn(
            "Please provide a description of your spot", form.errors["description"]
        )

    def test_no_location(self):
        """Test that missing location is rejected"""
        data = self.valid_data.copy()
        data["location"] = ""
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("location", form.errors)
        self.assertIn("Please select a location on the map", form.errors["location"])


class ListingSlotFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="slotformuser", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Slot Form Listing",
            location="456 Main St",
            rent_per_hour="15.00",
            description="Test slot form",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        # Use a future date so that the "start time not in past" rule is not triggered by default.
        self.future_date = date.today() + timedelta(days=1)

    def test_valid_slot_form(self):
        data = {
            "start_date": self.future_date.strftime("%Y-%m-%d"),
            "end_date": self.future_date.strftime("%Y-%m-%d"),
            "start_time": "10:00",
            "end_time": "10:30",
        }
        form = ListingSlotForm(data=data)
        self.assertTrue(form.is_valid())

    # Update this test to check for field-specific errors instead of __all__
    def test_invalid_date_order(self):
        data = {
            "start_date": (self.future_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date": self.future_date.strftime("%Y-%m-%d"),
            "start_time": "08:00",
            "end_time": "09:00",
        }
        form = ListingSlotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)
        self.assertIn(
            "End date cannot be before start date", str(form.errors["end_date"])
        )

    # Update this test to check for field-specific errors instead of __all__
    def test_invalid_time_order_same_day(self):
        data = {
            "start_date": self.future_date.strftime("%Y-%m-%d"),
            "end_date": self.future_date.strftime("%Y-%m-%d"),
            "start_time": "09:00",
            "end_time": "09:00",
        }
        form = ListingSlotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)
        self.assertIn(
            "End time must be later than start time", str(form.errors["end_time"])
        )

    # Add test for end date in the past
    def test_end_date_not_in_past(self):
        yesterday = date.today() - timedelta(days=1)
        data = {
            "start_date": self.future_date.strftime("%Y-%m-%d"),
            "end_date": yesterday.strftime("%Y-%m-%d"),
            "start_time": "10:00",
            "end_time": "11:00",
        }
        form = ListingSlotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)
        self.assertIn("End date cannot be in the past", str(form.errors["end_date"]))

    # Add test for start date in the past
    def test_start_date_not_in_past(self):
        yesterday = date.today() - timedelta(days=1)
        data = {
            "start_date": yesterday.strftime("%Y-%m-%d"),
            "end_date": self.future_date.strftime("%Y-%m-%d"),
            "start_time": "10:00",
            "end_time": "11:00",
        }
        form = ListingSlotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)
        self.assertIn(
            "Start date cannot be in the past", str(form.errors["start_date"])
        )

    # Update existing test to check field-specific errors
    def test_start_time_not_in_past(self):
        fixed_now = datetime.combine(date.today(), time(12, 0))

        with patch("listings.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.today.return_value = fixed_now
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime

            data = {
                "start_date": date.today().strftime("%Y-%m-%d"),
                "end_date": date.today().strftime("%Y-%m-%d"),
                "start_time": "09:00",  # 9am is before mocked now (12pm)
                "end_time": "14:00",  # 2pm is after mocked now
            }
            form = ListingSlotForm(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("start_time", form.errors)
            self.assertIn(
                "Start time cannot be in the past", str(form.errors["start_time"])
            )

    # Add test for end time in the past for today's date
    def test_end_time_not_in_past(self):
        fixed_now = datetime.combine(date.today(), time(12, 0))

        with patch("listings.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.today.return_value = fixed_now
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime

            data = {
                "start_date": date.today().strftime("%Y-%m-%d"),
                "end_date": date.today().strftime("%Y-%m-%d"),
                "start_time": "13:00",  # 1pm is after mocked now
                "end_time": "11:00",  # 11am is before mocked now
            }
            form = ListingSlotForm(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("end_time", form.errors)
            self.assertIn(
                "End time cannot be in the past", str(form.errors["end_time"])
            )


class ReviewFormTests(TestCase):
    def test_valid_review_form(self):
        data = {"rating": 4, "comment": "Good listing"}
        form = ReviewForm(data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_rating(self):
        data = {"rating": 6, "comment": "Too high rating"}
        form = ReviewForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("Rating must be between 1 and 5", str(form.errors))


class ValidateNonOverlappingSlotsTests(TestCase):
    class DummyForm:
        def __init__(self, cleaned_data):
            self.cleaned_data = cleaned_data
            self.errors = {}

        def add_error(self, field, error):
            if field not in self.errors:
                self.errors[field] = []
            self.errors[field].append(error)

    def setUp(self):
        # Use future dates for testing
        self.future_date = date.today() + timedelta(days=10)

    def test_non_overlapping(self):
        forms = [
            self.DummyForm(
                {
                    "start_date": self.future_date,
                    "start_time": "08:00",
                    "end_date": self.future_date,
                    "end_time": "09:00",
                    "DELETE": False,
                }
            ),
            self.DummyForm(
                {
                    "start_date": self.future_date,
                    "start_time": "09:00",
                    "end_date": self.future_date,
                    "end_time": "10:00",
                    "DELETE": False,
                }
            ),
        ]
        result = validate_non_overlapping_slots(forms)
        self.assertTrue(result)
        for form in forms:
            self.assertEqual(len(form.errors), 0)

    def test_overlapping(self):
        forms = [
            self.DummyForm(
                {
                    "start_date": self.future_date,
                    "start_time": "08:00",
                    "end_date": self.future_date,
                    "end_time": "09:30",
                    "DELETE": False,
                }
            ),
            self.DummyForm(
                {
                    "start_date": self.future_date,
                    "start_time": "09:00",
                    "end_date": self.future_date,
                    "end_time": "10:00",
                    "DELETE": False,
                }
            ),
        ]
        result = validate_non_overlapping_slots(forms)
        self.assertFalse(result)

        # Check that errors were added to both forms
        for form in forms:
            self.assertIn("start_date", form.errors)
            self.assertIn("end_date", form.errors)
            self.assertIn(
                "This slot overlaps with another slot", str(form.errors["start_date"])
            )

    def test_different_days_no_overlap(self):
        # Test slots on different days don't overlap
        forms = [
            self.DummyForm(
                {
                    "start_date": self.future_date,
                    "start_time": "08:00",
                    "end_date": self.future_date,
                    "end_time": "09:30",
                    "DELETE": False,
                }
            ),
            self.DummyForm(
                {
                    "start_date": self.future_date + timedelta(days=1),
                    "start_time": "08:00",
                    "end_date": self.future_date + timedelta(days=1),
                    "end_time": "09:30",
                    "DELETE": False,
                }
            ),
        ]
        result = validate_non_overlapping_slots(forms)
        self.assertTrue(result)
        for form in forms:
            self.assertEqual(len(form.errors), 0)

    def test_overnight_overlap(self):
        # Test overnight slots can overlap
        forms = [
            self.DummyForm(
                {
                    "start_date": self.future_date,
                    "start_time": "22:00",
                    "end_date": self.future_date + timedelta(days=1),
                    "end_time": "08:00",
                    "DELETE": False,
                }
            ),
            self.DummyForm(
                {
                    "start_date": self.future_date + timedelta(days=1),
                    "start_time": "07:00",
                    "end_date": self.future_date + timedelta(days=1),
                    "end_time": "10:00",
                    "DELETE": False,
                }
            ),
        ]
        result = validate_non_overlapping_slots(forms)
        self.assertFalse(result)

        # Check that errors were added to both forms
        for form in forms:
            self.assertIn("start_date", form.errors)
            self.assertIn("end_date", form.errors)
            self.assertIn(
                "This slot overlaps with another slot", str(form.errors["start_date"])
            )


class RecurringListingFormTests(TestCase):
    def setUp(self):
        # Future date for testing
        self.future_date = date.today() + timedelta(days=1)
        self.valid_daily_data = {
            "recurring_start_date": self.future_date.strftime("%Y-%m-%d"),
            "recurring_end_date": (self.future_date + timedelta(days=7)).strftime(
                "%Y-%m-%d"
            ),
            "recurring_start_time": "09:00",
            "recurring_end_time": "10:00",
            "recurring_overnight": False,
            "recurring_pattern": "daily",
        }
        self.valid_weekly_data = {
            "recurring_start_date": self.future_date.strftime("%Y-%m-%d"),
            "recurring_start_time": "09:00",
            "recurring_end_time": "10:00",
            "recurring_overnight": False,
            "recurring_pattern": "weekly",
            "recurring_weeks": 4,
        }

    def test_valid_daily_pattern(self):
        """Test valid daily pattern form"""
        form = RecurringListingForm(data=self.valid_daily_data)
        self.assertTrue(form.is_valid())

    def test_valid_weekly_pattern(self):
        """Test valid weekly pattern form"""
        form = RecurringListingForm(data=self.valid_weekly_data)
        self.assertTrue(form.is_valid())

    def test_daily_pattern_requires_end_date(self):
        """Test daily pattern requires end date"""
        data = self.valid_daily_data.copy()
        data["recurring_end_date"] = ""
        form = RecurringListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("recurring_end_date", form.errors)
        self.assertIn(
            "End date is required for daily pattern",
            str(form.errors["recurring_end_date"]),
        )

    def test_weekly_pattern_requires_weeks(self):
        """Test weekly pattern requires weeks"""
        data = self.valid_weekly_data.copy()
        data["recurring_weeks"] = ""
        form = RecurringListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("recurring_weeks", form.errors)
        self.assertIn(
            "Number of weeks is required for weekly pattern",
            str(form.errors["recurring_weeks"]),
        )

    def test_start_date_not_in_past(self):
        """Test start date cannot be in the past"""
        yesterday = date.today() - timedelta(days=1)
        data = self.valid_daily_data.copy()
        data["recurring_start_date"] = yesterday.strftime("%Y-%m-%d")
        form = RecurringListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("recurring_start_date", form.errors)
        self.assertIn(
            "Start date cannot be in the past", str(form.errors["recurring_start_date"])
        )

    def test_end_date_not_in_past(self):
        """Test end date cannot be in the past"""
        yesterday = date.today() - timedelta(days=1)
        data = self.valid_daily_data.copy()
        data["recurring_end_date"] = yesterday.strftime("%Y-%m-%d")
        form = RecurringListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("recurring_end_date", form.errors)
        self.assertIn(
            "End date cannot be in the past", str(form.errors["recurring_end_date"])
        )

    def test_end_date_after_start_date(self):
        """Test end date must be after start date"""
        data = self.valid_daily_data.copy()
        data["recurring_end_date"] = (date.today() - timedelta(days=2)).strftime(
            "%Y-%m-%d"
        )
        data["recurring_start_date"] = date.today().strftime("%Y-%m-%d")
        form = RecurringListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("recurring_end_date", form.errors)
        self.assertIn(
            "End date cannot be before start date",
            str(form.errors["recurring_end_date"]),
        )

    def test_end_time_after_start_time(self):
        """Test end time must be after start time when not overnight"""
        data = self.valid_daily_data.copy()
        data["recurring_start_time"] = "10:00"
        data["recurring_end_time"] = "09:00"
        data["recurring_overnight"] = False
        form = RecurringListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("recurring_end_time", form.errors)
        self.assertIn(
            "End time must be later than start time",
            str(form.errors["recurring_end_time"]),
        )

    def test_overnight_allows_end_time_before_start_time(self):
        """Test overnight flag allows end time before start time"""
        data = self.valid_daily_data.copy()
        data["recurring_start_time"] = "22:00"  # 10 PM
        data["recurring_end_time"] = "06:00"  # 6 AM (next day)
        data["recurring_overnight"] = True
        form = RecurringListingForm(data=data)
        self.assertTrue(form.is_valid())

    def test_start_time_not_in_past(self):
        """Test start time cannot be in the past for today's date"""
        fixed_now = datetime.combine(date.today(), time(12, 0))

        with patch("listings.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.today.return_value = fixed_now.date()
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime

            data = self.valid_daily_data.copy()
            data["recurring_start_date"] = date.today().strftime("%Y-%m-%d")
            data["recurring_start_time"] = "09:00"  # 9 AM (before mocked now at 12 PM)

            form = RecurringListingForm(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("recurring_start_time", form.errors)
            self.assertIn(
                "Start time cannot be in the past",
                str(form.errors["recurring_start_time"]),
            )

    def test_end_time_not_in_past(self):
        """Test end time cannot be in the past for today's date"""
        fixed_now = datetime.combine(date.today(), time(12, 0))

        with patch("listings.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.today.return_value = fixed_now.date()
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime

            data = self.valid_daily_data.copy()
            data["recurring_start_date"] = date.today().strftime("%Y-%m-%d")
            data["recurring_start_time"] = "13:00"  # 1 PM (after mocked now)
            data["recurring_end_time"] = "11:00"  # 11 AM (before mocked now)

            form = RecurringListingForm(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("recurring_end_time", form.errors)
            self.assertIn(
                "End time cannot be in the past", str(form.errors["recurring_end_time"])
            )

    def test_overnight_ignores_end_time_in_past(self):
        """Test overnight flag ignores end time being in the past"""
        fixed_now = datetime.combine(date.today(), time(12, 0))

        with patch("listings.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.today.return_value = fixed_now.date()
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime

            data = self.valid_daily_data.copy()
            data["recurring_start_date"] = date.today().strftime("%Y-%m-%d")
            data["recurring_start_time"] = "13:00"  # 1 PM (after mocked now)
            data["recurring_end_time"] = "11:00"  # 11 AM (before mocked now)
            data["recurring_overnight"] = True

            form = RecurringListingForm(data=data)
            self.assertTrue(form.is_valid())
