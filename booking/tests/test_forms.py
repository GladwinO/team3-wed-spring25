import datetime as dt
from django.test import TestCase
from booking.forms import BookingSlotForm
from booking.models import Listing
from django.contrib.auth.models import User


class BookingSlotFormTests(TestCase):
    def setUp(self):
        # Create a user first
        self.user = User.objects.create_user(username="testuser", password="password")

        # Create a listing with real fields
        self.listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="Test Location",
            rent_per_hour=10.0,
            description="Test description",
        )

        # Create listing slots that will determine the earliest/latest dates
        from listings.models import ListingSlot

        ListingSlot.objects.create(
            listing=self.listing,
            start_date=dt.date(2023, 1, 1),
            end_date=dt.date(2023, 12, 31),
            start_time=dt.time(8, 0),
            end_time=dt.time(18, 0),
        )

    def test_min_date_set_to_today_if_earliest_start_date_is_past(self):
        form = BookingSlotForm(listing=self.listing)
        today_str = dt.date.today().strftime("%Y-%m-%d")
        self.assertEqual(form.fields["start_date"].widget.attrs["min"], today_str)
        self.assertEqual(form.fields["end_date"].widget.attrs["min"], today_str)

    def test_min_date_set_to_earliest_start_date_if_future(self):
        # Delete existing slot
        from listings.models import ListingSlot

        ListingSlot.objects.filter(listing=self.listing).delete()

        # Create a new slot with future dates
        future_date = dt.date.today() + dt.timedelta(days=10)
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=future_date,
            end_date=future_date + dt.timedelta(days=30),
            start_time=dt.time(8, 0),
            end_time=dt.time(18, 0),
        )

        # Now the property will return the future date
        form = BookingSlotForm(listing=self.listing)
        future_date_str = future_date.strftime("%Y-%m-%d")
        self.assertEqual(form.fields["start_date"].widget.attrs["min"], future_date_str)
        self.assertEqual(form.fields["end_date"].widget.attrs["min"], future_date_str)

    def test_max_date_set_to_latest_end_date(self):
        form = BookingSlotForm(listing=self.listing)
        latest_date_str = self.listing.latest_end_datetime.date().strftime("%Y-%m-%d")
        self.assertEqual(form.fields["start_date"].widget.attrs["max"], latest_date_str)
        self.assertEqual(form.fields["end_date"].widget.attrs["max"], latest_date_str)

    def test_time_choices_filtered_based_on_listing_slots(self):
        form_data = {"start_date": "2023-01-01"}
        form = BookingSlotForm(data=form_data, listing=self.listing)

        # Create expected choices with half-hour increments
        expected_choices = []
        for hour in range(8, 18):  # Changed from 18 to 17 to exclude 17:30
            expected_choices.append((f"{hour:02d}:00", f"{hour:02d}:00"))
            expected_choices.append((f"{hour:02d}:30", f"{hour:02d}:30"))

        self.assertEqual(form.fields["start_time"].choices, expected_choices)
        self.assertEqual(form.fields["end_time"].choices, expected_choices)
