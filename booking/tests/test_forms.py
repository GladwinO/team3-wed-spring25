import datetime as dt

from django.test import TestCase
from django.contrib.auth import get_user_model

from booking.forms import BookingForm, BookingSlotForm, BookingSlotFormSet
from booking.models import Booking, BookingSlot
from listings.models import Listing, ListingSlot


class BookingFormTests(TestCase):
    def test_booking_form_valid(self):
        """Test that a BookingForm with a valid email is valid and has correct widget attributes."""
        form = BookingForm(data={"email": "test@example.com"})
        self.assertTrue(form.is_valid())
        self.assertIn(
            "form-control", form.fields["email"].widget.attrs.get("class", "")
        )
        self.assertEqual(
            form.fields["email"].help_text,
            "Enter your email for booking confirmation",
        )

    def test_booking_form_invalid(self):
        """Test that a BookingForm with an invalid email is invalid."""
        form = BookingForm(data={"email": "not-an-email"})
        self.assertFalse(form.is_valid())
        self.assertIn("Enter a valid email address", str(form.errors))


class BookingSlotFormTests(TestCase):
    def setUp(self):
        # Create a test user and listing.
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass"
        )
        self.listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="123 Test St, Test City",
            rent_per_hour="10.00",
            description="A test parking spot",
        )
        # Create a listing slot for tomorrow from 08:00 to 10:00.
        self.slot_date = dt.date.today() + dt.timedelta(days=1)
        self.listing_slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=self.slot_date,
            start_time=dt.time(8, 0),
            end_date=self.slot_date,
            end_time=dt.time(10, 0),
        )

    def test_widget_attrs_set(self):
        """
        Test that the BookingSlotForm __init__ sets the min and max date attributes
        on the date widgets based on the listing's slots.
        """
        form = BookingSlotForm(listing=self.listing)
        expected_min = max(self.listing_slot.start_date, dt.date.today())
        expected_min_str = expected_min.strftime("%Y-%m-%d")
        expected_max_str = self.listing_slot.end_date.strftime("%Y-%m-%d")
        self.assertEqual(
            form.fields["start_date"].widget.attrs.get("min"), expected_min_str
        )
        self.assertEqual(
            form.fields["end_date"].widget.attrs.get("min"), expected_min_str
        )
        self.assertEqual(
            form.fields["start_date"].widget.attrs.get("max"), expected_max_str
        )
        self.assertEqual(
            form.fields["end_date"].widget.attrs.get("max"), expected_max_str
        )

    def test_time_choices_filtering(self):
        """
        Test that when a valid start_date is provided in data,
        the BookingSlotForm limits the start_time and end_time choices
        based on the listing's available slot.
        """
        data = {"start_date": self.slot_date.strftime("%Y-%m-%d")}
        form = BookingSlotForm(data=data, listing=self.listing)
        # With the fix (using <= in the while loop), the valid times include "10:00".
        expected_choices = [
            ("08:00", "08:00"),
            ("08:30", "08:30"),
            ("09:00", "09:00"),
            ("09:30", "09:30"),
            ("10:00", "10:00"),
        ]
        self.assertEqual(form.fields["start_time"].choices, expected_choices)
        self.assertEqual(form.fields["end_time"].choices, expected_choices)

    def test_clean_date_order_error(self):
        """
        Test that clean() raises a validation error when start_date is after end_date.
        """
        form_data = {
            "start_date": (self.slot_date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date": self.slot_date.strftime("%Y-%m-%d"),
            "start_time": "08:00",
            "end_time": "09:00",
        }
        form = BookingSlotForm(data=form_data, listing=self.listing)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Start date cannot be after end date.",
            form.errors.get("__all__", []),
        )

    def test_clean_time_order_error(self):
        """
        Test that clean() raises a validation error when, on the same day,
        start_time is not earlier than end_time.
        """
        form_data = {
            "start_date": self.slot_date.strftime("%Y-%m-%d"),
            "end_date": self.slot_date.strftime("%Y-%m-%d"),
            "start_time": "09:00",
            "end_time": "09:00",
        }
        form = BookingSlotForm(data=form_data, listing=self.listing)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "End time must be later than start time on the same day.",
            form.errors.get("__all__", []),
        )

    def test_valid_clean(self):
        """
        Test that a BookingSlotForm with a proper time interval passes validation.
        """
        form_data = {
            "start_date": self.slot_date.strftime("%Y-%m-%d"),
            "end_date": self.slot_date.strftime("%Y-%m-%d"),
            "start_time": "08:00",
            "end_time": "08:30",
        }
        form = BookingSlotForm(data=form_data, listing=self.listing)
        self.assertTrue(form.is_valid())


class BookingSlotFormSetTests(TestCase):
    def setUp(self):
        # Create a test user and listing.
        self.user = get_user_model().objects.create_user(
            username="formsetuser", password="formsetpass"
        )
        self.listing = Listing.objects.create(
            user=self.user,
            title="Formset Listing",
            location="456 Form St, Test City",
            rent_per_hour="15.00",
            description="Listing for formset tests",
        )
        # Create a booking (with no initial booking slots).
        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="formset@test.com",
            total_price=0,
            status="PENDING",
        )
        # Use tomorrow’s date for booking slot forms.
        self.date = dt.date.today() + dt.timedelta(days=1)

    def formset_data(self, forms_data, prefix="slots"):
        """
        Helper to build POST data for the inline formset.
        `forms_data` should be a list of dictionaries, each representing a form's data.
        """
        data = {
            f"{prefix}-TOTAL_FORMS": str(len(forms_data)),
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }
        for i, form_data in enumerate(forms_data):
            for key, value in form_data.items():
                data[f"{prefix}-{i}-{key}"] = value
        return data

    def test_non_overlapping_intervals(self):
        """
        Test that a formset with two non-overlapping booking intervals is valid.
        """
        forms_data = [
            {
                "start_date": self.date.strftime("%Y-%m-%d"),
                "end_date": self.date.strftime("%Y-%m-%d"),
                "start_time": "08:00",
                "end_time": "08:30",
            },
            {
                "start_date": self.date.strftime("%Y-%m-%d"),
                "end_date": self.date.strftime("%Y-%m-%d"),
                "start_time": "09:00",
                "end_time": "09:30",
            },
        ]
        data = self.formset_data(forms_data, prefix="slots")
        formset = BookingSlotFormSet(
            data,
            instance=self.booking,
            form_kwargs={"listing": self.listing},
            queryset=BookingSlot.objects.none(),
            prefix="slots",
        )
        self.assertTrue(formset.is_valid(), formset.errors)

    def test_overlapping_intervals(self):
        """
        Test that a formset with overlapping booking intervals raises a validation error.
        """
        forms_data = [
            # First booking: 08:00 to 09:00.
            {
                "start_date": self.date.strftime("%Y-%m-%d"),
                "end_date": self.date.strftime("%Y-%m-%d"),
                "start_time": "08:00",
                "end_time": "09:00",
            },
            # Second booking: 08:30 to 09:30 (overlaps with the first).
            {
                "start_date": self.date.strftime("%Y-%m-%d"),
                "end_date": self.date.strftime("%Y-%m-%d"),
                "start_time": "08:30",
                "end_time": "09:30",
            },
        ]
        data = self.formset_data(forms_data, prefix="slots")
        formset = BookingSlotFormSet(
            data,
            instance=self.booking,
            form_kwargs={"listing": self.listing},
            queryset=BookingSlot.objects.none(),
            prefix="slots",
        )
        self.assertFalse(formset.is_valid())
        non_form_errors = formset.non_form_errors()
        self.assertTrue(
            any(
                "Booking intervals cannot overlap." in str(err)
                for err in non_form_errors
            ),
            f"Non-form errors: {non_form_errors}",
        )

    def test_delete_flag(self):
        """
        Test that when a form has DELETE checked, its interval is skipped
        during validation (so overlapping intervals with a deleted form are allowed).
        """
        forms_data = [
            # First booking with DELETE marked.
            {
                "start_date": self.date.strftime("%Y-%m-%d"),
                "end_date": self.date.strftime("%Y-%m-%d"),
                "start_time": "08:00",
                "end_time": "09:00",
                "DELETE": "on",
            },
            # Second booking overlaps with the first but should be valid since the first is marked for deletion.
            {
                "start_date": self.date.strftime("%Y-%m-%d"),
                "end_date": self.date.strftime("%Y-%m-%d"),
                "start_time": "08:30",
                "end_time": "09:30",
            },
        ]
        data = self.formset_data(forms_data, prefix="slots")
        formset = BookingSlotFormSet(
            data,
            instance=self.booking,
            form_kwargs={"listing": self.listing},
            queryset=BookingSlot.objects.none(),
            prefix="slots",
        )
        self.assertTrue(formset.is_valid(), formset.errors)
