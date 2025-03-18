from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from booking.models import Booking, BookingSlot
from listings.models import Listing


class BookingModelTest(TestCase):
    def setUp(self):
        # Create a test user and listing for the bookings
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.owner = User.objects.create_user(username="owner", password="12345")
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            description="A test parking spot",
            rent_per_hour=15.50,
            location="123 Test St",
        )
        # Create a booking
        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            total_price=Decimal("62.00"),
            status="PENDING",
        )

    def test_booking_creation(self):
        """Test that a booking is created correctly."""
        self.assertEqual(self.booking.user, self.user)
        self.assertEqual(self.booking.listing, self.listing)
        self.assertEqual(self.booking.total_price, Decimal("62.00"))
        self.assertEqual(self.booking.status, "PENDING")

    def test_booking_str_method(self):
        """Test the string representation of a booking."""
        expected_str = f"Booking #{self.booking.pk} by {self.user.username} for {self.listing.title}"
        self.assertEqual(str(self.booking), expected_str)

    def test_default_status(self):
        """Test that the default status is 'PENDING'."""
        new_booking = Booking.objects.create(
            user=self.user, listing=self.listing, total_price=Decimal("100.00")
        )
        self.assertEqual(new_booking.status, "PENDING")

    def test_status_choices(self):
        """Test that the status can only be one of the defined choices."""
        self.booking.status = "APPROVED"
        self.booking.save()
        self.assertEqual(self.booking.status, "APPROVED")

        self.booking.status = "DECLINED"
        self.booking.save()
        self.assertEqual(self.booking.status, "DECLINED")

    def test_timestamps(self):
        """Test that created_at and updated_at are set."""
        self.assertIsNotNone(self.booking.created_at)
        self.assertIsNotNone(self.booking.updated_at)

        # Test that updated_at changes on save
        original_updated_at = self.booking.updated_at
        self.booking.status = "APPROVED"
        self.booking.save()
        self.assertNotEqual(self.booking.updated_at, original_updated_at)


class BookingSlotModelTest(TestCase):
    def setUp(self):
        # Create a test user and listing for the bookings
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.owner = User.objects.create_user(username="owner", password="12345")
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            description="A test parking spot",
            rent_per_hour=15.50,
            location="123 Test St",
        )

        # Create a booking
        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            total_price=Decimal("62.00"),
            status="PENDING",
        )

        # Create a booking slot
        self.today = datetime.date.today()
        self.start_time = datetime.time(10, 0)
        self.end_time = datetime.time(12, 0)

        self.booking_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=self.today,
            start_time=self.start_time,
            end_date=self.today,
            end_time=self.end_time,
        )

    def test_booking_slot_creation(self):
        """Test that a booking slot is created correctly."""
        self.assertEqual(self.booking_slot.booking, self.booking)
        self.assertEqual(self.booking_slot.start_date, self.today)
        self.assertEqual(self.booking_slot.start_time, self.start_time)
        self.assertEqual(self.booking_slot.end_date, self.today)
        self.assertEqual(self.booking_slot.end_time, self.end_time)

    def test_booking_slot_str_method(self):
        """Test the string representation of a booking slot."""
        expected_str = (
            f"BookingSlot for Booking #{self.booking.pk}: "
            f"{self.today} {self.start_time} - {self.today} {self.end_time}"
        )
        self.assertEqual(str(self.booking_slot), expected_str)

    def test_booking_relationship(self):
        """Test that the booking relationship works correctly."""
        # Check that the booking has this slot
        self.assertEqual(self.booking.slots.count(), 1)
        self.assertEqual(self.booking.slots.first(), self.booking_slot)

    def test_multiple_booking_slots(self):
        """Test that a booking can have multiple slots."""
        tomorrow = self.today + datetime.timedelta(days=1)
        second_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=tomorrow,
            start_time=self.start_time,
            end_date=tomorrow,
            end_time=self.end_time,
        )

        self.assertEqual(self.booking.slots.count(), 2)
        self.assertIn(self.booking_slot, self.booking.slots.all())
        self.assertIn(second_slot, self.booking.slots.all())

    def test_cascade_delete(self):
        """Test that deleting a booking also deletes its slots."""
        booking_id = self.booking.id
        self.booking.delete()
        self.assertEqual(BookingSlot.objects.filter(booking_id=booking_id).count(), 0)
