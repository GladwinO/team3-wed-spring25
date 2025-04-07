import datetime as dt

from django.test import TestCase
from django.contrib.auth import get_user_model

from booking.utils import (
    subtract_interval,
    merge_intervals,
    block_out_booking,
    restore_booking_availability,
)
from listings.models import Listing, ListingSlot
from booking.models import Booking, BookingSlot

User = get_user_model()


class UtilsTests(TestCase):
    def setUp(self):
        # Create a test user and listing for booking-related tests.
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="123 Test St",
            rent_per_hour="10.00",
            description="A test listing",
        )
        # Use a fixed test date (tomorrow) for availability.
        self.test_date = dt.date.today() + dt.timedelta(days=1)

    # ---- Tests for subtract_interval ----
    def test_subtract_interval_no_overlap_after(self):
        # Booking starts at or after the slot ends: no overlap.
        slot_start = dt.datetime(2025, 1, 1, 10, 0)
        slot_end = dt.datetime(2025, 1, 1, 20, 0)
        booking_start = dt.datetime(2025, 1, 1, 20, 0)
        booking_end = dt.datetime(2025, 1, 1, 21, 0)
        result = subtract_interval(slot_start, slot_end, booking_start, booking_end)
        self.assertEqual(result, [(slot_start, slot_end)])

    def test_subtract_interval_no_overlap_before(self):
        # Booking ends at or before the slot starts: no overlap.
        slot_start = dt.datetime(2025, 1, 1, 10, 0)
        slot_end = dt.datetime(2025, 1, 1, 20, 0)
        booking_start = dt.datetime(2025, 1, 1, 8, 0)
        booking_end = dt.datetime(2025, 1, 1, 10, 0)
        result = subtract_interval(slot_start, slot_end, booking_start, booking_end)
        self.assertEqual(result, [(slot_start, slot_end)])

    def test_subtract_interval_middle_overlap(self):
        # Booking is fully inside the slot.
        slot_start = dt.datetime(2025, 1, 1, 10, 0)
        slot_end = dt.datetime(2025, 1, 1, 20, 0)
        booking_start = dt.datetime(2025, 1, 1, 12, 0)
        booking_end = dt.datetime(2025, 1, 1, 18, 0)
        result = subtract_interval(slot_start, slot_end, booking_start, booking_end)
        expected = [
            (dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 12, 0)),
            (dt.datetime(2025, 1, 1, 18, 0), dt.datetime(2025, 1, 1, 20, 0)),
        ]
        self.assertEqual(result, expected)

    def test_subtract_interval_left_overlap(self):
        # Booking overlaps the left part of the slot.
        slot_start = dt.datetime(2025, 1, 1, 10, 0)
        slot_end = dt.datetime(2025, 1, 1, 20, 0)
        booking_start = dt.datetime(2025, 1, 1, 8, 0)
        booking_end = dt.datetime(2025, 1, 1, 12, 0)
        result = subtract_interval(slot_start, slot_end, booking_start, booking_end)
        expected = [(dt.datetime(2025, 1, 1, 12, 0), dt.datetime(2025, 1, 1, 20, 0))]
        self.assertEqual(result, expected)

    def test_subtract_interval_right_overlap(self):
        # Booking overlaps the right part of the slot.
        slot_start = dt.datetime(2025, 1, 1, 10, 0)
        slot_end = dt.datetime(2025, 1, 1, 20, 0)
        booking_start = dt.datetime(2025, 1, 1, 18, 0)
        booking_end = dt.datetime(2025, 1, 1, 22, 0)
        result = subtract_interval(slot_start, slot_end, booking_start, booking_end)
        expected = [(dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 18, 0))]
        self.assertEqual(result, expected)

    def test_subtract_interval_full_cover(self):
        # Booking completely covers the slot.
        slot_start = dt.datetime(2025, 1, 1, 10, 0)
        slot_end = dt.datetime(2025, 1, 1, 20, 0)
        booking_start = dt.datetime(2025, 1, 1, 9, 0)
        booking_end = dt.datetime(2025, 1, 1, 21, 0)
        result = subtract_interval(slot_start, slot_end, booking_start, booking_end)
        expected = []
        self.assertEqual(result, expected)

    # ---- Tests for merge_intervals ----
    def test_merge_intervals_empty(self):
        intervals = []
        result = merge_intervals(intervals)
        self.assertEqual(result, [])

    def test_merge_intervals_overlapping(self):
        intervals = [
            (dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 12, 0)),
            (dt.datetime(2025, 1, 1, 11, 0), dt.datetime(2025, 1, 1, 14, 0)),
        ]
        result = merge_intervals(intervals)
        expected = [(dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 14, 0))]
        self.assertEqual(result, expected)

    def test_merge_intervals_adjacent(self):
        intervals = [
            (dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 12, 0)),
            (dt.datetime(2025, 1, 1, 12, 0), dt.datetime(2025, 1, 1, 15, 0)),
        ]
        result = merge_intervals(intervals)
        expected = [(dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 15, 0))]
        self.assertEqual(result, expected)

    def test_merge_intervals_non_overlapping(self):
        intervals = [
            (dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 12, 0)),
            (dt.datetime(2025, 1, 1, 13, 0), dt.datetime(2025, 1, 1, 15, 0)),
        ]
        result = merge_intervals(intervals)
        expected = [
            (dt.datetime(2025, 1, 1, 10, 0), dt.datetime(2025, 1, 1, 12, 0)),
            (dt.datetime(2025, 1, 1, 13, 0), dt.datetime(2025, 1, 1, 15, 0)),
        ]
        self.assertEqual(result, expected)

    # ---- Tests for block_out_booking ----
    def test_block_out_booking(self):
        # Create an initial availability slot from 10:00 to 20:00 on test_date.
        start_time = dt.time(10, 0)
        end_time = dt.time(20, 0)
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=self.test_date,
            start_time=start_time,
            end_date=self.test_date,
            end_time=end_time,
        )
        # Create a booking with one booking slot from 12:00 to 14:00.
        booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="test@booking.com",
            total_price=0,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=self.test_date,
            start_time=dt.time(12, 0),
            end_date=self.test_date,
            end_time=dt.time(14, 0),
        )
        # Block out the booking from the listing's availability.
        block_out_booking(self.listing, booking)
        # The resulting availability should be split into two intervals:
        # [10:00, 12:00] and [14:00, 20:00]
        slots = list(self.listing.slots.all())
        self.assertEqual(len(slots), 2)
        expected_intervals = [
            (dt.time(10, 0), dt.time(12, 0)),
            (dt.time(14, 0), dt.time(20, 0)),
        ]
        for slot in slots:
            interval = (slot.start_time, slot.end_time)
            self.assertIn(interval, expected_intervals)

    # ---- Tests for restore_booking_availability ----
    def test_restore_booking_availability(self):
        # Set up listing with two separate availability slots:
        # one from 10:00 to 12:00 and another from 14:00 to 20:00.
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=self.test_date,
            start_time=dt.time(10, 0),
            end_date=self.test_date,
            end_time=dt.time(12, 0),
        )
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=self.test_date,
            start_time=dt.time(14, 0),
            end_date=self.test_date,
            end_time=dt.time(20, 0),
        )
        # Create a booking with one booking slot from 12:00 to 14:00.
        booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="test@booking.com",
            total_price=0,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=self.test_date,
            start_time=dt.time(12, 0),
            end_date=self.test_date,
            end_time=dt.time(14, 0),
        )
        # Restore the booking's availability.
        restore_booking_availability(self.listing, booking)
        # The restored availability should merge into one interval: [10:00, 20:00]
        slots = list(self.listing.slots.all())
        self.assertEqual(len(slots), 1)
        slot = slots[0]
        self.assertEqual(slot.start_time, dt.time(10, 0))
        self.assertEqual(slot.end_time, dt.time(20, 0))
