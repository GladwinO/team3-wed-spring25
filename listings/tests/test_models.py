import datetime as dt
from django.test import TestCase
from django.contrib.auth import get_user_model
from listings.models import Listing, ListingSlot, Review
from listings.utilities import simplify_location  # used by Listing.location_name

User = get_user_model()


class ListingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_location_name_property(self):
        location = "123, Main Street, City, State, 12345, Country"
        listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location=location,
            rent_per_hour="10.00",
            description="Test description",
        )
        # location_name should be simplified using the utility.
        self.assertEqual(listing.location_name, simplify_location(location))

    def test_avg_rating_and_rating_count(self):
        listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="123 Main St",
            rent_per_hour="10.00",
            description="Test description",
        )
        # When there are no reviews, avg_rating is None and count is 0.
        self.assertIsNone(listing.avg_rating)
        self.assertEqual(listing.rating_count, 0)
        # Create two reviews.
        from booking.models import (
            Booking,
        )  # review.booking is a OneToOneField to booking.Booking

        booking1 = Booking.objects.create(
            user=self.user,
            listing=listing,
            email="a@example.com",
            total_price=0,
            status="APPROVED",
        )
        booking2 = Booking.objects.create(
            user=self.user,
            listing=listing,
            email="b@example.com",
            total_price=0,
            status="APPROVED",
        )
        Review.objects.create(
            booking=booking1, listing=listing, user=self.user, rating=4, comment="Good"
        )
        Review.objects.create(
            booking=booking2, listing=listing, user=self.user, rating=2, comment="Bad"
        )
        self.assertEqual(listing.avg_rating, 3)
        self.assertEqual(listing.rating_count, 2)

    def test_str_method(self):
        listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="123 Main St",
            rent_per_hour="10.00",
            description="Test description",
        )
        self.assertEqual(str(listing), "Test Listing - 123 Main St")

    def test_is_available_for_range_single_slot(self):
        listing = Listing.objects.create(
            user=self.user,
            title="Availability Listing",
            location="123 Main St",
            rent_per_hour="10.00",
            description="Test description",
        )
        day = dt.date(2025, 1, 1)
        # Create a slot from 05:00 to 09:00.
        ListingSlot.objects.create(
            listing=listing,
            start_date=day,
            start_time=dt.time(5, 0),
            end_date=day,
            end_time=dt.time(9, 0),
        )
        start_dt = dt.datetime.combine(day, dt.time(5, 0))
        end_dt = dt.datetime.combine(day, dt.time(9, 0))
        self.assertTrue(listing.is_available_for_range(start_dt, end_dt))
        # A subrange is available.
        sub_start = dt.datetime.combine(day, dt.time(6, 0))
        sub_end = dt.datetime.combine(day, dt.time(8, 0))
        self.assertTrue(listing.is_available_for_range(sub_start, sub_end))
        # A range extending beyond slot end fails.
        self.assertFalse(
            listing.is_available_for_range(
                start_dt, dt.datetime.combine(day, dt.time(9, 30))
            )
        )

    def test_is_available_for_range_multiple_slots(self):
        listing = Listing.objects.create(
            user=self.user,
            title="Multi Slot Listing",
            location="123 Main St",
            rent_per_hour="10.00",
            description="Test description",
        )
        day = dt.date(2025, 1, 1)
        # Create two contiguous slots: 05:00-07:00 and 07:00-09:00.
        ListingSlot.objects.create(
            listing=listing,
            start_date=day,
            start_time=dt.time(5, 0),
            end_date=day,
            end_time=dt.time(7, 0),
        )
        ListingSlot.objects.create(
            listing=listing,
            start_date=day,
            start_time=dt.time(7, 0),
            end_date=day,
            end_time=dt.time(9, 0),
        )
        start_dt = dt.datetime.combine(day, dt.time(5, 0))
        end_dt = dt.datetime.combine(day, dt.time(9, 0))
        self.assertTrue(listing.is_available_for_range(start_dt, end_dt))
        # Requesting beyond available range returns False.
        self.assertFalse(
            listing.is_available_for_range(
                start_dt, dt.datetime.combine(day, dt.time(9, 30))
            )
        )

    def test_earliest_and_latest_datetime(self):
        listing = Listing.objects.create(
            user=self.user,
            title="Datetime Listing",
            location="123 Main St",
            rent_per_hour="10.00",
            description="Test description",
        )
        day = dt.date(2025, 1, 1)
        slot1 = ListingSlot.objects.create(
            listing=listing,
            start_date=day,
            start_time=dt.time(6, 0),
            end_date=day,
            end_time=dt.time(8, 0),
        )
        print(slot1)
        slot2 = ListingSlot.objects.create(
            listing=listing,
            start_date=day,
            start_time=dt.time(9, 0),
            end_date=day,
            end_time=dt.time(11, 0),
        )
        print(slot2)
        expected_earliest = dt.datetime.combine(day, dt.time(6, 0))
        expected_latest = dt.datetime.combine(day, dt.time(11, 0))
        self.assertEqual(listing.earliest_start_datetime, expected_earliest)
        self.assertEqual(listing.latest_end_datetime, expected_latest)


class ListingSlotModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="slotuser", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Slot Test Listing",
            location="456 Main St",
            rent_per_hour="15.00",
            description="Slot test description",
        )
        self.day = dt.date(2025, 1, 2)

    def test_str_method(self):
        slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=self.day,
            start_time=dt.time(8, 0),
            end_date=self.day,
            end_time=dt.time(10, 0),
        )
        expected = (
            f"{self.listing.title} slot: {self.day} 08:00:00 - {self.day} 10:00:00"
        )
        self.assertEqual(str(slot), expected)


class ReviewModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reviewuser", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Review Test Listing",
            location="789 Main St",
            rent_per_hour="20.00",
            description="Review test description",
        )
        from booking.models import Booking

        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="review@example.com",
            total_price=0,
            status="APPROVED",
        )

    def test_str_method(self):
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            user=self.user,
            rating=5,
            comment="Excellent",
        )
        expected = f"Review for {self.listing.title} by {self.user.username}"
        self.assertEqual(str(review), expected)
