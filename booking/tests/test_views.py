from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
import json
import datetime as dt
from booking.models import Booking, BookingSlot
from listings.models import Listing, ListingSlot
from listings.models import Review

User = get_user_model()


class AvailableTimesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")
        self.listing = Listing.objects.create(
            user=self.user, title="Test Parking", rent_per_hour=10.0
        )
        # Create a listing slot for today and tomorrow
        today = timezone.now().date()
        tomorrow = today + dt.timedelta(days=1)
        self.slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=today,
            end_date=tomorrow,
            start_time=dt.time(8, 0),
            end_time=dt.time(20, 0),
        )

    def test_missing_parameters(self):
        response = self.client.get(reverse("available_times"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["times"], [])

    def test_invalid_date_format(self):
        response = self.client.get(
            reverse("available_times"),
            {"listing_id": self.listing.id, "date": "invalid-date"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["times"], [])

    def test_with_reference_date(self):
        today = timezone.now().date().strftime("%Y-%m-%d")
        response = self.client.get(
            reverse("available_times"),
            {"listing_id": self.listing.id, "date": today, "ref_date": today},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("08:00", data["times"])

    def test_with_time_constraints(self):
        today = timezone.now().date().strftime("%Y-%m-%d")
        response = self.client.get(
            reverse("available_times"),
            {
                "listing_id": self.listing.id,
                "date": today,
                "min_time": "12:00",
                "max_time": "15:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("12:00", data["times"])
        self.assertIn("15:00", data["times"])
        self.assertNotIn("11:30", data["times"])
        self.assertNotIn("15:30", data["times"])


class BookListingViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="password")
        self.renter = User.objects.create_user(username="renter", password="password")
        self.listing = Listing.objects.create(
            user=self.owner, title="Test Parking", rent_per_hour=10.0
        )
        # Create a listing slot
        today = timezone.now().date()
        tomorrow = today + dt.timedelta(days=1)
        self.slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=today,
            end_date=tomorrow,
            start_time=dt.time(8, 0),
            end_time=dt.time(20, 0),
        )

    def test_owner_cannot_book_own_listing(self):
        self.client.login(username="owner", password="password")
        response = self.client.get(reverse("book_listing", args=[self.listing.id]))
        self.assertRedirects(response, reverse("view_listings"))

    def test_get_booking_form(self):
        self.client.login(username="renter", password="password")
        response = self.client.get(reverse("book_listing", args=[self.listing.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/book_listing.html")
        self.assertContains(response, "Test Parking")


class CancelBookingViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="password")
        self.renter = User.objects.create_user(username="renter", password="password")
        self.other_user = User.objects.create_user(
            username="other", password="password"
        )
        self.listing = Listing.objects.create(
            user=self.owner, title="Test Parking", rent_per_hour=10.0
        )
        self.booking = Booking.objects.create(
            user=self.renter, listing=self.listing, status="PENDING", total_price=100.0
        )

    def test_cancel_own_booking(self):
        self.client.login(username="renter", password="password")
        response = self.client.get(reverse("cancel_booking", args=[self.booking.id]))
        self.assertRedirects(response, reverse("my_bookings"))
        self.assertFalse(Booking.objects.filter(id=self.booking.id).exists())

    def test_cannot_cancel_others_booking(self):
        self.client.login(username="other", password="password")
        response = self.client.get(reverse("cancel_booking", args=[self.booking.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Booking.objects.filter(id=self.booking.id).exists())


class ManageBookingViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="password")
        self.renter = User.objects.create_user(username="renter", password="password")
        self.listing = Listing.objects.create(
            user=self.owner, title="Test Parking", rent_per_hour=10.0
        )
        self.booking = Booking.objects.create(
            user=self.renter, listing=self.listing, status="PENDING", total_price=100.0
        )

    def test_approve_booking(self):
        self.client.login(username="owner", password="password")
        response = self.client.get(
            reverse("manage_booking", args=[self.booking.id, "approve"])
        )
        self.assertRedirects(response, reverse("manage_listings"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "APPROVED")

    def test_decline_booking(self):
        self.client.login(username="owner", password="password")
        response = self.client.get(
            reverse("manage_booking", args=[self.booking.id, "decline"])
        )
        self.assertRedirects(response, reverse("manage_listings"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "DECLINED")

    def test_non_owner_cannot_manage(self):
        self.client.login(username="renter", password="password")
        response = self.client.get(
            reverse("manage_booking", args=[self.booking.id, "approve"])
        )
        self.assertRedirects(response, reverse("my_bookings"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "PENDING")


class ReviewBookingViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="password")
        self.renter = User.objects.create_user(username="renter", password="password")
        self.listing = Listing.objects.create(
            user=self.owner, title="Test Parking", rent_per_hour=10.0
        )
        # Create booking with slots
        self.booking = Booking.objects.create(
            user=self.renter, listing=self.listing, status="APPROVED", total_price=100.0
        )
        # Past booking slot
        yesterday = timezone.now().date() - dt.timedelta(days=1)
        self.booking_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=yesterday,
            end_date=yesterday,
            start_time=dt.time(8, 0),
            end_time=dt.time(10, 0),
        )

    def test_get_review_form(self):
        self.client.login(username="renter", password="password")
        response = self.client.get(reverse("review_booking", args=[self.booking.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/review_booking.html")

    def test_submit_review(self):
        self.client.login(username="renter", password="password")
        response = self.client.post(
            reverse("review_booking", args=[self.booking.id]),
            {"rating": 5, "comment": "Great parking spot!"},
        )
        self.assertRedirects(response, reverse("my_bookings"))
        self.assertTrue(Review.objects.filter(booking=self.booking).exists())


class MyBookingsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.listing = Listing.objects.create(
            user=User.objects.create_user(username="owner", password="password"),
            title="Test Parking",
            rent_per_hour=10.0,
        )
        self.booking = Booking.objects.create(
            user=self.user, listing=self.listing, status="APPROVED", total_price=100.0
        )
        today = timezone.now().date()
        self.booking_slot = BookingSlot.objects.create(
            booking=self.booking,
            start_date=today,
            end_date=today,
            start_time=dt.time(14, 0),
            end_time=dt.time(16, 0),
        )

    def test_my_bookings_view(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("my_bookings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/my_bookings.html")
        self.assertContains(response, "Test Parking")
        self.assertIn("bookings", response.context)
        self.assertEqual(len(response.context["bookings"]), 1)
        self.assertIn("slots_info", response.context["bookings"][0].__dict__)
