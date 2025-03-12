from django.test import TestCase
from datetime import date, timedelta
from ..forms import ListingForm, ReviewForm


class ListingFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            "title": "Test Listing",
            "location": "Test Location",
            "rent_per_hour": 10,
            "description": "Test Description",
            "available_from": date.today() + timedelta(days=1),
            "available_until": date.today() + timedelta(days=2),
            "available_time_from": "08:00",
            "available_time_until": "18:00",
        }

    def test_listing_form_valid(self):
        form = ListingForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_listing_form_invalid_past_available_from(self):
        data = self.valid_data.copy()
        data["available_from"] = date.today() - timedelta(days=1)
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("available_from", form.errors)

    def test_listing_form_invalid_past_available_until(self):
        data = self.valid_data.copy()
        data["available_until"] = date.today() - timedelta(days=1)
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("available_until", form.errors)

    def test_listing_form_invalid_available_until_before_available_from(self):
        data = self.valid_data.copy()
        data["available_until"] = date.today() + timedelta(days=1)
        data["available_from"] = date.today() + timedelta(days=2)
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("available_until", form.errors)

    def test_listing_form_invalid_rent_per_hour(self):
        data = self.valid_data.copy()
        data["rent_per_hour"] = -5
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("Rent per hour must be a positive number", form.errors["__all__"])

    def test_listing_form_invalid_time_range(self):
        data = self.valid_data.copy()
        # Set same date for both from and until to test time validation
        today = date.today() + timedelta(days=1)
        data["available_from"] = today
        data["available_until"] = today
        data["available_time_from"] = "18:00"
        data["available_time_until"] = "08:00"
        form = ListingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("available_time_until", form.errors)
        self.assertIn(
            "When start and end dates are the same, the end time must be after the start time",
            str(form.errors["available_time_until"]),
        )


class ReviewFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            "rating": 5,
            "comment": "Great place!",
        }

    def test_review_form_valid(self):
        form = ReviewForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_review_form_invalid_rating(self):
        data = self.valid_data.copy()
        data["rating"] = 6
        form = ReviewForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

        data["rating"] = 0
        form = ReviewForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)
