from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from booking.models import Booking, BookingSlot
from listings.models import Listing, Review  # Import the Review model
from django.utils import timezone
from unittest.mock import patch


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


class BookingPropertiesTest(TestCase):
    def setUp(self):
        # Create test user and listing
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
            status="APPROVED",
        )
        # Create a current date/time for testing
        self.now = timezone.now()

    def test_is_reviewed_property(self):
        """Test the is_reviewed property."""
        # Initially, booking should not be reviewed
        self.assertFalse(self.booking.is_reviewed)

        # Create an actual Review instance
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            user=self.user,
            rating=5,
            comment="Great parking spot!",
        )

        # Use the review variable explicitly
        self.assertEqual(review.rating, 5)
        self.assertTrue(self.booking.is_reviewed)

    @patch("django.utils.timezone.now")
    def test_is_within_24_hours_property(self, mock_now):
        """Test the is_within_24_hours property."""
        # Set the current time
        mock_now.return_value = self.now

        # Test case 1: Slot starting within 24 hours
        start = self.now + datetime.timedelta(hours=12)  # 12 hours from now
        end = start + datetime.timedelta(hours=2)  # 2 hours duration
        slot_within_24h = BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        self.assertTrue(self.booking.is_within_24_hours)

        # Remove that slot and create one more than 24 hours away
        slot_within_24h.delete()
        start = self.now + datetime.timedelta(days=2)  # 2 days from now
        end = start + datetime.timedelta(hours=2)  # 2 hours duration
        BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        self.assertFalse(self.booking.is_within_24_hours)

    @patch("django.utils.timezone.now")
    def test_has_passed_property(self, mock_now):
        """Test the has_passed property."""
        # Set the current time
        mock_now.return_value = self.now

        # Test case 1: No slots
        self.assertFalse(self.booking.has_passed)

        # Test case 2: All slots have passed
        start = self.now - datetime.timedelta(days=2)  # 2 days ago
        end = start + datetime.timedelta(hours=2)  # 2 hours duration
        past_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        # Use past_slot explicitly
        self.assertEqual(past_slot.booking, self.booking)
        self.assertTrue(self.booking.has_passed)

        # Test case 3: Not all slots have passed
        start = self.now + datetime.timedelta(days=1)  # 1 day from now
        end = start + datetime.timedelta(hours=2)  # 2 hours duration
        future_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        # Use future_slot explicitly
        self.assertEqual(future_slot.booking, self.booking)
        self.assertFalse(self.booking.has_passed)

    @patch("django.utils.timezone.now")
    def test_can_be_reviewed_property(self, mock_now):
        """Test the can_be_reviewed property."""
        # Set the current time
        mock_now.return_value = self.now

        # Create a past slot
        start = self.now - datetime.timedelta(days=2)  # 2 days ago
        end = start + datetime.timedelta(hours=2)  # 2 hours duration
        past_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )

        # Test case 1: Approved, has passed, not reviewed
        self.assertTrue(self.booking.can_be_reviewed)

        # Test case 2: Not approved, has passed, not reviewed
        self.booking.status = "PENDING"
        self.booking.save()
        self.assertFalse(self.booking.can_be_reviewed)

        # Test case 3: Approved, has passed, already reviewed
        self.booking.status = "APPROVED"
        self.booking.save()

        # Create an actual Review instance
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            user=self.user,  # Add the user who created the review
            rating=4,
            comment="Nice parking spot!",
        )

        self.assertFalse(self.booking.can_be_reviewed)

        # Test case 4: Approved, not passed, not reviewed
        review.delete()  # Remove the review
        past_slot.delete()
        start = self.now + datetime.timedelta(days=1)  # 1 day from now
        end = start + datetime.timedelta(hours=2)  # 2 hours duration
        BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        self.assertFalse(self.booking.can_be_reviewed)

    @patch("django.utils.timezone.now")
    def test_is_ongoing_property(self, mock_now):
        """Test the is_ongoing property."""
        # Set the current time
        mock_now.return_value = self.now

        # Test case 1: No slots
        self.assertFalse(self.booking.is_ongoing)

        # Test case 2: Ongoing slot (current time is between start and end)
        two_hours_ago = self.now - datetime.timedelta(hours=4)
        two_hours_future = self.now + datetime.timedelta(hours=4)

        ongoing_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=two_hours_ago.date(),
            start_time=two_hours_ago.time(),
            end_date=two_hours_future.date(),
            end_time=two_hours_future.time(),
        )
        self.assertTrue(self.booking.is_ongoing)

        # Test case 3: Not ongoing (future slot)
        ongoing_slot.delete()
        start = self.now + datetime.timedelta(days=1)  # 1 day from now
        end = start + datetime.timedelta(hours=2)
        future_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        self.assertFalse(self.booking.is_ongoing)

        # Test case 4: Not ongoing (past slot)
        future_slot.delete()
        start = self.now - datetime.timedelta(days=2)  # 2 days ago
        end = start + datetime.timedelta(hours=2)
        past_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=start.date(),  # Use the date of the start time
            start_time=start.time(),  # Use the time of the start
            end_date=end.date(),  # Ensure end date matches the start date
            end_time=end.time(),  # Use the time of the end
        )
        self.assertFalse(self.booking.is_ongoing)
        past_slot.delete()
