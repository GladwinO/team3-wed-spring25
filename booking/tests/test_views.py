import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from listings.models import Listing, Review
from ..models import Booking
from ..forms import BookingForm


class BookingViewsTest(TestCase):
    def setUp(self):
        # Create two test users - one as a booker, one as a host
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )
        self.host_user = User.objects.create_user(
            username="hostuser", email="host@example.com", password="hostpassword123"
        )

        # Create test listing
        self.listing = Listing.objects.create(
            user=self.host_user,
            title="Test Listing",
            location="Test Location",
            rent_per_hour=Decimal("50.00"),
            description="Test description",
            available_time_from=datetime.time(9, 0),
            available_time_until=datetime.time(17, 0),
        )

        # Create a test booking
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            booking_date=tomorrow,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            total_price=Decimal("100.00"),
            status="PENDING",
        )

        # Create a past booking for testing review functionality
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.past_booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            booking_date=yesterday,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            total_price=Decimal("100.00"),
            status="APPROVED",
        )

        # Create a client
        self.client = Client()

    def test_book_listing_get(self):
        """Test getting the booking form page"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Send GET request
        response = self.client.get(reverse("book_listing", args=[self.listing.id]))

        # Check response status code
        self.assertEqual(response.status_code, 200)

        # Check correct template was used
        self.assertTemplateUsed(response, "booking/book_listing.html")

        # Check form is in context
        self.assertIsInstance(response.context["form"], BookingForm)

        # Check listing is in context
        self.assertEqual(response.context["listing"], self.listing)

    def test_book_listing_post_success(self):
        """Test successful booking form submission"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Prepare form data
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        form_data = {
            "booking_date": tomorrow,
            "start_time": "10:00",
            "end_time": "11:00",
        }

        # Record booking count
        booking_count_before = Booking.objects.count()

        # Submit form
        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), form_data
        )

        # Check redirect to my bookings page
        self.assertRedirects(response, reverse("my_bookings"))

        # Check new booking was created
        self.assertEqual(Booking.objects.count(), booking_count_before + 1)

        # Get newly created booking and check its properties
        new_booking = Booking.objects.last()
        self.assertEqual(new_booking.user, self.user)
        self.assertEqual(new_booking.listing, self.listing)
        self.assertEqual(new_booking.booking_date, tomorrow)
        self.assertEqual(new_booking.start_time, datetime.time(10, 0))
        self.assertEqual(new_booking.end_time, datetime.time(11, 0))
        self.assertEqual(new_booking.status, "PENDING")

    def test_book_listing_unauthenticated(self):
        """Test unauthenticated user is redirected to login page"""
        # Visit booking page
        response = self.client.get(reverse("book_listing", args=[self.listing.id]))

        # Check redirect to login page
        login_url = (
            reverse("login")
            + f'?next={reverse("book_listing", args=[self.listing.id])}'
        )
        self.assertRedirects(response, login_url)

    def test_cancel_booking(self):
        """Test booking cancellation functionality"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Record booking count
        booking_count_before = Booking.objects.count()

        # Send cancellation request
        response = self.client.post(reverse("cancel_booking", args=[self.booking.id]))

        # Check redirect to my bookings page
        self.assertRedirects(response, reverse("my_bookings"))

        # Check booking was deleted
        self.assertEqual(Booking.objects.count(), booking_count_before - 1)
        with self.assertRaises(Booking.DoesNotExist):
            Booking.objects.get(id=self.booking.id)

    def test_manage_booking_approve(self):
        """Test host approving booking request"""
        # Login host
        self.client.login(username="hostuser", password="hostpassword123")

        # Send approval request
        response = self.client.post(
            reverse("manage_booking", args=[self.booking.id, "approve"])
        )

        # Check redirect to manage listings page
        self.assertRedirects(response, reverse("manage_listings"))

        # Check booking status was updated
        booking = Booking.objects.get(id=self.booking.id)
        self.assertEqual(booking.status, "APPROVED")

    def test_manage_booking_decline(self):
        """Test host declining booking request"""
        # Login host
        self.client.login(username="hostuser", password="hostpassword123")

        # Send decline request
        response = self.client.post(
            reverse("manage_booking", args=[self.booking.id, "decline"])
        )

        # Check redirect to manage listings page
        self.assertRedirects(response, reverse("manage_listings"))

        # Check booking status was updated
        booking = Booking.objects.get(id=self.booking.id)
        self.assertEqual(booking.status, "DECLINED")

    def test_manage_booking_unauthorized(self):
        """Test non-host user cannot manage booking"""
        # Login regular user (non-host)
        self.client.login(username="testuser", password="testpassword123")

        # Try to approve booking
        response = self.client.post(
            reverse("manage_booking", args=[self.booking.id, "approve"])
        )

        # Check redirect to my bookings page
        self.assertRedirects(response, reverse("my_bookings"))

        # Check booking status remains unchanged
        booking = Booking.objects.get(id=self.booking.id)
        self.assertEqual(booking.status, "PENDING")

    def test_review_booking_get(self):
        """Test getting review form page"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Send GET request
        response = self.client.get(
            reverse("review_booking", args=[self.past_booking.id])
        )

        # Check response status code
        self.assertEqual(response.status_code, 200)

        # Check correct template was used
        self.assertTemplateUsed(response, "booking/review_booking.html")

    def test_review_booking_post(self):
        """Test submitting review form"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Prepare form data
        form_data = {"rating": 4, "comment": "Great experience!"}

        # Submit form
        response = self.client.post(
            reverse("review_booking", args=[self.past_booking.id]), form_data
        )

        # Check redirect to my bookings page
        self.assertRedirects(response, reverse("my_bookings"))

        # Check review was created
        self.assertTrue(Review.objects.filter(booking=self.past_booking).exists())
        review = Review.objects.get(booking=self.past_booking)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, "Great experience!")
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.listing, self.listing)

    def test_review_future_booking(self):
        """Test cannot review future bookings"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Try to review future booking
        response = self.client.get(reverse("review_booking", args=[self.booking.id]))

        # Check redirect to my bookings page
        self.assertRedirects(response, reverse("my_bookings"))

        # Check no review was created
        self.assertFalse(Review.objects.filter(booking=self.booking).exists())

    def test_my_bookings(self):
        """Test my bookings list page"""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Send GET request
        response = self.client.get(reverse("my_bookings"))

        # Check response status code
        self.assertEqual(response.status_code, 200)

        # Check correct template was used
        self.assertTemplateUsed(response, "booking/my_bookings.html")

        # Check context contains user's bookings
        bookings = response.context["bookings"]
        self.assertEqual(len(bookings), 2)

        # Check bookings are ordered by created_at in descending order
        self.assertEqual(bookings[0], self.past_booking)
        self.assertEqual(bookings[1], self.booking)

        # Check past bookings are marked as started
        self.assertTrue(bookings[0].has_started)

        # Check future bookings are marked as not started
        self.assertFalse(bookings[1].has_started)
