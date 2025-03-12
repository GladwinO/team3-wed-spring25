import datetime
from django.test import TestCase
from datetime import date, timedelta
from ..forms import BookingForm, HALF_HOUR_CHOICES


class TestBookingForm(TestCase):
    def setUp(self):
        # Create a mock listing object
        class MockListing:
            def __init__(self):
                self.available_time_from = datetime.time(9, 0)  # 9:00 AM
                self.available_time_until = datetime.time(17, 0)  # 5:00 PM

        self.listing = MockListing()
        self.tomorrow = date.today() + timedelta(days=1)

    def test_init_default(self):
        """Test form initialization without a listing"""
        form = BookingForm()
        self.assertEqual(form.fields["start_time"].choices, HALF_HOUR_CHOICES)
        self.assertEqual(form.fields["end_time"].choices, HALF_HOUR_CHOICES)

    def test_init_with_listing(self):
        """Test form initialization with a listing"""
        form = BookingForm(listing=self.listing)

        # Check that time choices are limited by the listing's available times
        expected_choices = [
            (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
            for hour in range(24)
            for minute in (0, 30)
            if datetime.time(hour, minute) >= self.listing.available_time_from
            and datetime.time(hour, minute) <= self.listing.available_time_until
        ]

        self.assertEqual(form.fields["start_time"].choices, expected_choices)
        self.assertEqual(form.fields["end_time"].choices, expected_choices)

    def test_clean_booking_date_past_date(self):
        """Test validation rejects past dates"""
        yesterday = date.today() - timedelta(days=1)
        form_data = {
            "booking_date": yesterday,
            "start_time": "10:00",
            "end_time": "11:00",
        }
        form = BookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("booking_date", form.errors)
        self.assertIn("past date", form.errors["booking_date"][0])

    def test_clean_start_time_before_end_time(self):
        """Test validation requires start time before end time"""
        form_data = {
            "booking_date": self.tomorrow,
            "start_time": "11:00",
            "end_time": "10:00",
        }
        form = BookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Start Time must be before End Time", str(form.errors))

    def test_clean_equal_times(self):
        """Test validation rejects equal start and end times"""
        form_data = {
            "booking_date": self.tomorrow,
            "start_time": "10:00",
            "end_time": "10:00",
        }
        form = BookingForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Start Time must be before End Time", str(form.errors))

    def test_clean_invalid_time_format(self):
        """Test validation rejects invalid time formats"""
        form_data = {
            "booking_date": self.tomorrow,
            "start_time": "invalid",
            "end_time": "11:00",
        }
        form = BookingForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_valid_form(self):
        """Test form accepts valid data"""
        form_data = {
            "booking_date": self.tomorrow,
            "start_time": "10:00",
            "end_time": "11:00",
        }
        form = BookingForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Check that times were converted to datetime.time objects
        self.assertIsInstance(form.cleaned_data["start_time"], datetime.time)
        self.assertIsInstance(form.cleaned_data["end_time"], datetime.time)
