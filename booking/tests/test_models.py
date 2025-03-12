import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from listings.models import Listing
from ..models import Booking


class TestBookingModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        self.listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="Test Location",
            rent_per_hour=Decimal("50.00"),
            description="Test description",
            available_time_from=datetime.time(9, 0),
            available_time_until=datetime.time(17, 0),
        )

        # 创建测试预订
        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            booking_date=datetime.date(2025, 5, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            total_price=Decimal("100.00"),
        )

    def test_booking_creation(self):
        self.assertEqual(self.booking.user, self.user)
        self.assertEqual(self.booking.listing, self.listing)
        self.assertEqual(self.booking.booking_date, datetime.date(2025, 5, 20))
        self.assertEqual(self.booking.start_time, datetime.time(10, 0))
        self.assertEqual(self.booking.end_time, datetime.time(12, 0))
        self.assertEqual(self.booking.total_price, Decimal("100.00"))
        self.assertIsNotNone(self.booking.created_at)
        self.assertIsNotNone(self.booking.updated_at)

    def test_default_status(self):
        self.assertEqual(self.booking.status, "PENDING")

    def test_string_representation(self):
        expected_string = f"{self.listing.title} booked by {self.user.username} on {self.booking.booking_date}"
        self.assertEqual(str(self.booking), expected_string)

    def test_update_status(self):
        self.booking.status = "APPROVED"
        self.booking.save()
        updated_booking = Booking.objects.get(id=self.booking.id)
        self.assertEqual(updated_booking.status, "APPROVED")

    def test_booking_relation(self):
        user_bookings = self.user.booking_set.all()
        listing_bookings = self.listing.booking_set.all()

        self.assertEqual(user_bookings.count(), 1)
        self.assertEqual(listing_bookings.count(), 1)
        self.assertEqual(user_bookings.first(), self.booking)
        self.assertEqual(listing_bookings.first(), self.booking)

    def test_multiple_bookings(self):
        booking2 = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            booking_date=datetime.date(2025, 5, 21),
            start_time=datetime.time(14, 0),
            end_time=datetime.time(16, 0),
            total_price=Decimal("100.00"),
        )
        booking2.status = "DECLINED"

        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(self.user.booking_set.count(), 2)

    def test_status_choices(self):
        valid_statuses = ["PENDING", "APPROVED", "DECLINED"]
        for status in valid_statuses:
            self.booking.status = status
            self.booking.save()
            self.assertEqual(Booking.objects.get(id=self.booking.id).status, status)
