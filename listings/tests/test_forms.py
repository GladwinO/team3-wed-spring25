from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User

from listings.forms import (
    ListingForm,
    ListingSlotForm,
    validate_non_overlapping_slots,
    ReviewForm,
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

    def test_invalid_date_order(self):
        data = {
            "start_date": (self.future_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date": self.future_date.strftime("%Y-%m-%d"),
            "start_time": "08:00",
            "end_time": "09:00",
        }
        form = ListingSlotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Start date cannot be after end date.", form.errors.get("__all__", [])
        )

    def test_invalid_time_order_same_day(self):
        data = {
            "start_date": self.future_date.strftime("%Y-%m-%d"),
            "end_date": self.future_date.strftime("%Y-%m-%d"),
            "start_time": "09:00",
            "end_time": "09:00",
        }
        form = ListingSlotForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "End time must be later than start time on the same day.",
            form.errors.get("__all__", []),
        )

    def test_start_time_not_in_past(self):
        # Fix "now" by patching datetime in listings.forms.
        fixed_now = datetime.combine(date.today(), time(12, 0))
        from listings.forms import ListingSlotForm

        with patch("listings.forms.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.today.return_value = fixed_now
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime
            data = {
                "start_date": date.today().strftime("%Y-%m-%d"),
                "end_date": date.today().strftime("%Y-%m-%d"),
                "start_time": "09:00",
                "end_time": "09:30",
            }
            form = ListingSlotForm(data=data)
            self.assertFalse(form.is_valid())
            # Check for the custom error message substring.
            self.assertIn("Start time cannot be in the past", str(form.errors))


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

    def test_non_overlapping(self):
        forms = [
            self.DummyForm(
                {
                    "start_date": date(2025, 1, 1),
                    "start_time": "08:00",
                    "end_date": date(2025, 1, 1),
                    "end_time": "09:00",
                    "DELETE": False,
                }
            ),
            self.DummyForm(
                {
                    "start_date": date(2025, 1, 1),
                    "start_time": "09:00",
                    "end_date": date(2025, 1, 1),
                    "end_time": "10:00",
                    "DELETE": False,
                }
            ),
        ]
        try:
            validate_non_overlapping_slots(forms)
        except Exception as e:
            self.fail(f"Unexpected exception: {e}")

    def test_overlapping(self):
        forms = [
            self.DummyForm(
                {
                    "start_date": date(2025, 1, 1),
                    "start_time": "08:00",
                    "end_date": date(2025, 1, 1),
                    "end_time": "09:30",
                    "DELETE": False,
                }
            ),
            self.DummyForm(
                {
                    "start_date": date(2025, 1, 1),
                    "start_time": "09:00",
                    "end_date": date(2025, 1, 1),
                    "end_time": "10:00",
                    "DELETE": False,
                }
            ),
        ]
        with self.assertRaises(Exception) as context:
            validate_non_overlapping_slots(forms)
        self.assertIn("Availability slots cannot overlap", str(context.exception))
