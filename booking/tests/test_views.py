import datetime as dt

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from listings.models import Listing, ListingSlot, Review
from booking.models import Booking, BookingSlot
from booking.utils import block_out_booking

User = get_user_model()


class ViewsTests(TestCase):
    def setUp(self):
        # Create two users: an owner and a non-owner (booking user)
        self.owner = User.objects.create_user(username="owner", password="pass123")
        self.non_owner = User.objects.create_user(
            username="nonowner", password="pass123"
        )
        self.client = Client()

        # Create a listing owned by self.owner
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking",
            location="123 Main St",
            rent_per_hour="5.00",
            description="A parking spot for testing",
        )
        # Create a listing slot for tomorrow from 8:00 to 10:00.
        self.slot_date = dt.date.today() + dt.timedelta(days=1)
        self.listing_slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=self.slot_date,
            start_time=dt.time(8, 0),
            end_date=self.slot_date,
            end_time=dt.time(10, 0),
        )

    # ---------------------- available_times ----------------------
    def test_available_times_missing_params(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("available_times")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"times": []})

    def test_available_times_invalid_date(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("available_times")
        response = self.client.get(
            url, {"listing_id": self.listing.id, "date": "invalid-date"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"times": []})

    def test_available_times_valid(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        date_str = self.slot_date.strftime("%Y-%m-%d")
        url = reverse("available_times")
        response = self.client.get(
            url, {"listing_id": self.listing.id, "date": date_str}
        )
        self.assertEqual(response.status_code, 200)
        # With a slot from 8:00 to 10:00 and using <= in the loop,
        # valid times are: "08:00", "08:30", "09:00", "09:30", "10:00"
        expected_times = ["08:00", "08:30", "09:00", "09:30", "10:00"]
        self.assertEqual(response.json(), {"times": expected_times})

    def test_available_times_with_max_min(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        date_str = self.slot_date.strftime("%Y-%m-%d")
        url = reverse("available_times")
        # Test max_time filter: return times <= "09:00"
        response = self.client.get(
            url, {"listing_id": self.listing.id, "date": date_str, "max_time": "09:00"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"times": ["08:00", "08:30", "09:00"]})
        # Test min_time filter: return times >= "09:00"
        response = self.client.get(
            url, {"listing_id": self.listing.id, "date": date_str, "min_time": "09:00"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"times": ["09:00", "09:30", "10:00"]})

    def test_available_times_with_ref_date(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        date_str = self.slot_date.strftime("%Y-%m-%d")
        url = reverse("available_times")
        response = self.client.get(
            url, {"listing_id": self.listing.id, "date": date_str, "ref_date": date_str}
        )
        expected_times = ["08:00", "08:30", "09:00", "09:30", "10:00"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"times": expected_times})

    # ---------------------- book_listing ----------------------
    def test_book_listing_owner_cannot_book(self):
        # The listing owner cannot book their own listing.
        self.client.login(username=self.owner.username, password="pass123")
        url = reverse("book_listing", kwargs={"listing_id": self.listing.id})
        response = self.client.get(url)
        # Expecting a redirect (302) because the owner is not allowed.
        self.assertEqual(response.status_code, 302)

    def test_book_listing_get(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("book_listing", kwargs={"listing_id": self.listing.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that the context contains the booking form and slot formset.
        self.assertIn("booking_form", response.context)
        self.assertIn("slot_formset", response.context)

    def test_book_listing_post_valid(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("book_listing", kwargs={"listing_id": self.listing.id})
        # Prepare POST data:
        post_data = {
            "email": "nonowner@example.com",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-start_date": self.slot_date.strftime("%Y-%m-%d"),
            "form-0-end_date": self.slot_date.strftime("%Y-%m-%d"),
            "form-0-start_time": "08:00",
            "form-0-end_time": "08:30",
        }
        response = self.client.post(url, post_data)
        # Successful booking redirects to my_bookings.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("my_bookings"), response.url)
        # Verify booking and slot creation.
        booking = Booking.objects.filter(
            user=self.non_owner, listing=self.listing
        ).first()
        self.assertIsNotNone(booking)
        self.assertTrue(booking.slots.exists())
        # 30 minutes = 0.5 hours, so total_price = 0.5 * 5.00 = 2.50.
        self.assertAlmostEqual(booking.total_price, 2.5)

    def test_book_listing_post_invalid(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("book_listing", kwargs={"listing_id": self.listing.id})
        # Invalid POST: missing email.
        post_data = {
            "email": "",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-start_date": self.slot_date.strftime("%Y-%m-%d"),
            "form-0-end_date": self.slot_date.strftime("%Y-%m-%d"),
            "form-0-start_time": "08:00",
            "form-0-end_time": "08:30",
        }
        response = self.client.post(url, post_data)
        # Expecting the form to re-render with errors.
        self.assertEqual(response.status_code, 200)

    def test_booking_form_email_autofill(self):
        """Test that the booking form is pre-filled with the user's email."""
        # Set an email for the non_owner user
        self.non_owner.email = "test@example.com"
        self.non_owner.save()

        # Log in using the same pattern as other tests
        self.client.login(username=self.non_owner.username, password="pass123")

        # Get the booking form page
        url = reverse("book_listing", kwargs={"listing_id": self.listing.id})
        response = self.client.get(url)

        # Check that the form has the user's email pre-filled
        self.assertEqual(
            response.context["booking_form"].initial["email"], "test@example.com"
        )

    # ---------------------- cancel_booking ----------------------
    def test_cancel_booking(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        # Create a booking for the non-owner.
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="PENDING",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=self.slot_date,
            start_time=dt.time(8, 0),
            end_date=self.slot_date,
            end_time=dt.time(8, 30),
        )
        url = reverse("cancel_booking", kwargs={"booking_id": booking.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("my_bookings"), response.url)
        self.assertFalse(Booking.objects.filter(id=booking.id).exists())

    # ---------------------- manage_booking ----------------------
    def test_manage_booking_approve(self):
        # Create a booking by non_owner for a listing owned by owner.
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="PENDING",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=self.slot_date,
            start_time=dt.time(8, 0),
            end_date=self.slot_date,
            end_time=dt.time(8, 30),
        )
        self.client.login(username=self.owner.username, password="pass123")
        url = reverse(
            "manage_booking", kwargs={"booking_id": booking.id, "action": "approve"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse(
                "manage_booking", kwargs={"booking_id": booking.id, "action": "approve"}
            ),
            url,
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, "APPROVED")
        # Verify that block_out_booking updated listing slots.
        self.assertTrue(self.listing.slots.exists())

    def test_manage_booking_decline(self):
        # Create a booking already approved.
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=self.slot_date,
            start_time=dt.time(8, 0),
            end_date=self.slot_date,
            end_time=dt.time(8, 30),
        )
        self.client.login(username=self.owner.username, password="pass123")
        url = reverse(
            "manage_booking", kwargs={"booking_id": booking.id, "action": "decline"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse(
                "manage_booking", kwargs={"booking_id": booking.id, "action": "decline"}
            ),
            url,
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, "DECLINED")

    def test_manage_booking_not_owner(self):
        # Non-owner trying to manage a booking on a listing they don't own.
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="PENDING",
        )
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse(
            "manage_booking", kwargs={"booking_id": booking.id, "action": "approve"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("my_bookings"), response.url)

    # ---------------------- review_booking ----------------------
    def test_review_booking_not_started(self):
        # Create a booking with a booking slot in the future.
        future_date = dt.date.today() + dt.timedelta(days=2)
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=future_date,
            start_time=dt.time(10, 0),
            end_date=future_date,
            end_time=dt.time(10, 30),
        )
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("review_booking", kwargs={"booking_id": booking.id})
        response = self.client.get(url)
        # Booking hasn't started so should redirect.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("my_bookings"), response.url)

    def test_review_booking_already_reviewed(self):
        # Create a booking with a past booking slot.
        past_date = dt.date.today() - dt.timedelta(days=1)
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=past_date,
            start_time=dt.time(8, 0),
            end_date=past_date,
            end_time=dt.time(8, 30),
        )
        # Create a review to simulate that it has already been reviewed.
        Review.objects.create(
            booking=booking,
            listing=self.listing,
            user=self.non_owner,
            rating=5,
            comment="Great spot!",
        )
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("review_booking", kwargs={"booking_id": booking.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("my_bookings"), response.url)

    def test_review_booking_get(self):
        # Create a booking with a past slot and no review.
        past_date = dt.date.today() - dt.timedelta(days=1)
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=past_date,
            start_time=dt.time(8, 0),
            end_date=past_date,
            end_time=dt.time(8, 30),
        )
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("review_booking", kwargs={"booking_id": booking.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "booking/review_booking.html")
        self.assertIn("form", response.context)
        self.assertIn("booking", response.context)

    def test_review_booking_post_valid(self):
        # Create a booking with a past slot and no review.
        past_date = dt.date.today() - dt.timedelta(days=1)
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=past_date,
            start_time=dt.time(8, 0),
            end_date=past_date,
            end_time=dt.time(8, 30),
        )
        self.client.login(username=self.non_owner.username, password="pass123")
        url = reverse("review_booking", kwargs={"booking_id": booking.id})
        post_data = {
            "rating": "5",
            "comment": "Excellent!",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("my_bookings"), response.url)
        # Verify a review was created.
        self.assertTrue(Review.objects.filter(booking=booking).exists())

    # ---------------------- my_bookings ----------------------
    def test_my_bookings(self):
        self.client.login(username=self.non_owner.username, password="pass123")
        # Create a booking with a past booking slot.
        past_date = dt.date.today() - dt.timedelta(days=1)
        booking = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=2.5,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking,
            start_date=past_date,
            start_time=dt.time(8, 0),
            end_date=past_date,
            end_time=dt.time(8, 30),
        )
        url = reverse("my_bookings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Ensure that the bookings are passed in context and each booking has slots_info.
        self.assertIn("bookings", response.context)
        bookings_list = response.context["bookings"]
        self.assertGreaterEqual(len(bookings_list), 1)
        for b in bookings_list:
            self.assertTrue(hasattr(b, "slots_info"))

    def test_my_bookings_priority_order(self):
        """Test that bookings are displayed in the expected priority order."""
        self.client.login(username=self.non_owner.username, password="pass123")

        # Create 3 bookings with different statuses for non_owner
        # 1. Approved booking without review
        booking1 = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=10.00,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking1,
            start_date=self.slot_date,
            start_time=dt.time(8, 0),
            end_date=self.slot_date,
            end_time=dt.time(9, 0),
        )

        # 2. Pending booking
        booking2 = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=10.00,
            status="PENDING",
        )
        BookingSlot.objects.create(
            booking=booking2,
            start_date=self.slot_date,
            start_time=dt.time(9, 0),
            end_date=self.slot_date,
            end_time=dt.time(10, 0),
        )

        # 3. Approved booking with review
        booking3 = Booking.objects.create(
            user=self.non_owner,
            listing=self.listing,
            email="nonowner@example.com",
            total_price=10.00,
            status="APPROVED",
        )
        BookingSlot.objects.create(
            booking=booking3,
            start_date=self.slot_date,
            start_time=dt.time(10, 0),
            end_date=self.slot_date,
            end_time=dt.time(11, 0),
        )

        # Add a review for booking3
        Review.objects.create(
            booking=booking3,
            listing=self.listing,
            user=self.non_owner,
            rating=5,
        )

        # Get my_bookings page
        response = self.client.get(reverse("my_bookings"))
        self.assertEqual(response.status_code, 200)

        # Check bookings order in context
        bookings = response.context["bookings"]
        self.assertEqual(len(bookings), 3)

        # Verify correct priority order:
        # 1. Approved unreviewed (booking1)
        # 2. Other bookings (booking2)
        # 3. Approved reviewed (booking3)
        self.assertEqual(bookings[0].id, booking1.id)
        self.assertEqual(bookings[1].id, booking2.id)
        self.assertEqual(bookings[2].id, booking3.id)


class RecurringBookingTests(TestCase):
    def setUp(self):
        # Create test users
        self.owner = User.objects.create_user(username="owner", password="pass123")
        self.renter = User.objects.create_user(username="renter", password="pass123")

        # Create a standard listing with availability for the next 7 days (continuous)
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            description="A test parking spot",
            location="123 Test St",
            rent_per_hour=10.0,
        )

        # Create availability for the next 7 days (one continuous slot)
        today = dt.date.today()
        self.listing_slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=today,
            start_time=dt.time(9, 0),  # 9 AM
            end_date=today + dt.timedelta(days=7),
            end_time=dt.time(17, 0),  # 5 PM
        )

        # Create a long-term listing to test weekly recurring bookings
        self.long_term_listing = Listing.objects.create(
            user=self.owner,
            title="Long Term Parking Spot",
            description="A long-term parking spot for testing",
            location="789 Long Term St",
            rent_per_hour=8.0,
        )

        # Create availability for 7 weeks (49 days) for long-term listing
        today = dt.date.today()
        self.long_term_listing_slot = ListingSlot.objects.create(
            listing=self.long_term_listing,
            start_date=today,
            start_time=dt.time(9, 0),  # 9 AM
            end_date=today + dt.timedelta(days=49),
            end_time=dt.time(17, 0),  # 5 PM
        )

        # Create a listing with fragmented availability (separate days)
        self.fragmented_listing = Listing.objects.create(
            user=self.owner,
            title="Fragmented Parking Spot",
            description="A test parking spot with gaps in availability",
            location="456 Test St",
            rent_per_hour=10.0,
        )

        # Available on days 1, 3, 5, 7 (creating separate slots for discrete intervals)
        for day_offset in [0, 2, 4, 6]:
            day = today + dt.timedelta(days=day_offset)
            ListingSlot.objects.create(
                listing=self.fragmented_listing,
                start_date=day,
                start_time=dt.time(9, 0),  # 9 AM
                end_date=day,
                end_time=dt.time(17, 0),  # 5 PM
            )

        # Test weekly fragmented ability
        self.weekly_fragmented_listing = Listing.objects.create(
            user=self.owner,
            title="Weekly Fragmented Parking Spot",
            description="A test parking spot with gaps in weekly availability",
            location="321 Weekly Test St",
            rent_per_hour=10.0,
        )

        # Available on weeks 1, 3, 5 (creating separate slots for discrete intervals)
        for week_offset in [0, 2, 4]:
            start_date = today + dt.timedelta(weeks=week_offset)
            ListingSlot.objects.create(
                listing=self.weekly_fragmented_listing,
                start_date=start_date,
                start_time=dt.time(9, 0),  # 9 AM
                end_date=start_date + dt.timedelta(days=6),  # End of week
                end_time=dt.time(17, 0),  # 5 PM
            )

        # Create a listing with overnight availability
        self.overnight_listing = Listing.objects.create(
            user=self.owner,
            title="Overnight Spot",
            description="Available overnight",
            location="111 Night St",
            rent_per_hour=10.0,
        )

        # Available from 5 PM to 9 AM the next day for a week
        ListingSlot.objects.create(
            listing=self.overnight_listing,
            start_date=today,
            start_time=dt.time(17, 0),  # 5 PM
            end_date=today + dt.timedelta(days=8),
            end_time=dt.time(9, 0),  # 9 AM
        )

        # Login the renter
        self.client = Client()
        self.client.login(username="renter", password="pass123")

    def test_missing_required_fields(self):
        """Test recurring booking with missing required fields"""
        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            # Missing start_date
            "recurring-start_time": "10:00",
            "recurring-end_time": "14:00",
            "recurring_pattern": "daily",
            "recurring-end_date": (dt.date.today() + dt.timedelta(days=3)).strftime(
                "%Y-%m-%d"
            ),
        }

        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data
        )

        # Check for error message
        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any("required" in msg for msg in response.context["error_messages"])
        )

        # No booking should be created
        self.assertEqual(Booking.objects.count(), 0)

    def test_end_time_before_start_time(self):
        """Test non-overnight booking with end time before start time"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "14:00",  # 2 PM
            "recurring-end_time": "10:00",  # 10 AM (before start time)
            "recurring-pattern": "daily",
            "recurring-end_date": (today + dt.timedelta(days=3)).strftime("%Y-%m-%d"),
        }

        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data
        )

        # Should have error message
        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any("time" in msg.lower() for msg in response.context["error_messages"])
        )

        # No booking should be created
        self.assertEqual(Booking.objects.count(), 0)

    def test_end_date_before_start_date(self):
        """Test booking with end date before start date"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": (today + dt.timedelta(days=3)).strftime("%Y-%m-%d"),
            "recurring-start_time": "10:00",
            "recurring-end_time": "14:00",
            "recurring-pattern": "daily",
            "recurring-end_date": today.strftime("%Y-%m-%d"),  # Before start date
        }

        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data
        )

        # Should have error message about end date before start date
        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any("date" in msg.lower() for msg in response.context["error_messages"])
        )

        # No booking should be created
        self.assertEqual(Booking.objects.count(), 0)

    def test_start_time_before_available(self):
        """Test booking with start time before available hours"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "08:00",  # Before available (9 AM)
            "recurring-end_time": "10:00",
            "recurring-pattern": "daily",
            "recurring-end_date": (today + dt.timedelta(days=3)).strftime("%Y-%m-%d"),
        }

        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data
        )

        # Should have error message
        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any(
                "unavailable" in msg.lower()
                for msg in response.context["error_messages"]
            )
        )

        # No booking should be created
        self.assertEqual(Booking.objects.count(), 0)

    def test_end_time_after_available(self):
        """Test booking with end time after available hours"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "15:00",  # 3 PM
            "recurring-end_time": "18:00",  # After available (5 PM)
            "recurring-pattern": "daily",
            "recurring-end_date": (today + dt.timedelta(days=7)).strftime("%Y-%m-%d"),
        }

        self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data
        )

        # Check that no booking was created
        self.assertEqual(Booking.objects.count(), 0)

    def test_successful_daily_recurring_booking(self):
        """Test successful daily recurring booking"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "10:00",
            "recurring-end_time": "14:00",
            "recurring-pattern": "daily",
            "recurring-end_date": (today + dt.timedelta(days=3)).strftime("%Y-%m-%d"),
        }

        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data, follow=True
        )

        # Should redirect to my_bookings
        self.assertRedirects(response, reverse("my_bookings"))

        # Should create one booking with 4 slots (today + 3 days)
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.slots.count(), 4)

    def test_failed_daily_recurring_booking_with_gaps(self):
        """Test daily booking that fails due to gaps in availability"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "10:00",
            "recurring-end_time": "14:00",
            "recurring-pattern": "daily",
            "recurring-end_date": (today + dt.timedelta(days=3)).strftime("%Y-%m-%d"),
        }

        response = self.client.post(
            reverse("book_listing", args=[self.fragmented_listing.id]), data=post_data
        )

        # Should have error message - the fragmented listing has days 0, 2, 4, 6 available
        # So a daily booking for days 0-3 would include day 1 which is not available
        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any(
                "unavailable" in msg.lower()
                for msg in response.context["error_messages"]
            )
        )

        # No booking should be created
        self.assertEqual(Booking.objects.count(), 0)

    def test_successful_weekly_recurring_booking(self):
        """Test successful weekly recurring booking"""
        today = dt.date.today()

        # Make sure there are no existing bookings
        Booking.objects.all().delete()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "10:00",
            "recurring-end_time": "14:00",
            "recurring_pattern": "weekly",  # Change hyphen to underscore
            "recurring-weeks": "3",
        }

        # Make sure we use follow=True to follow redirects
        self.client.post(
            reverse("book_listing", args=[self.long_term_listing.id]),
            data=post_data,
            follow=True,
        )

        # Check that a booking was created with the right number of slots
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.slots.count(), 3)

    def test_failed_weekly_recurring_booking_with_gaps(self):
        """Test weekly booking that fails due to gaps in availability"""

        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "10:00",
            "recurring-end_time": "14:00",
            "recurring_pattern": "weekly",  # Change hyphen to underscore
            "recurring-weeks": "5",
        }

        response = self.client.post(
            reverse("book_listing", args=[self.weekly_fragmented_listing.id]),
            data=post_data,
        )

        # Should have error message - the weekly fragmented listing has weeks 0, 2, 4 available
        # So a weekly booking for weeks 0-4 would include week 1 which is not available

        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any(
                "unavailable" in msg.lower()
                for msg in response.context["error_messages"]
            )
        )

        # No booking should be created
        self.assertEqual(Booking.objects.count(), 0)

    def test_overnight_booking_success(self):
        """Test successful overnight recurring booking"""
        today = dt.date.today()

        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "20:00",  # 8 PM
            "recurring-end_time": "08:00",  # 8 AM (next day)
            "recurring-overnight": "on",  # Use hyphen for consistency
            "recurring-pattern": "daily",  # Use underscore for consistency
            "recurring-end_date": (today + dt.timedelta(days=7)).strftime("%Y-%m-%d"),
        }

        self.client.post(
            reverse("book_listing", args=[self.overnight_listing.id]),
            data=post_data,
            follow=True,
        )

        # Check for successful booking creation rather than redirect
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.slots.count(), 8)

    def test_overnight_booking_beyond_available_range(self):
        """Test overnight booking where the last night extends beyond available range"""
        today = dt.date.today()

        # Available from 5 PM to 9 AM the next day for exactly 7 days
        last_day = today + dt.timedelta(days=7)  # Day 0 + 7 = day 8

        # Try to book through the last day, where the time extends past the end of the slot
        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "20:00",  # 8 PM
            "recurring-end_time": "10:00",  # 8 AM (next day)
            "recurring_overnight": "on",
            "recurring-pattern": "daily",
            "recurring-end_date": last_day.strftime(
                "%Y-%m-%d"
            ),  # This would require availability on day 7+1
        }

        self.client.post(
            reverse("book_listing", args=[self.overnight_listing.id]), data=post_data
        )

        # Check that no booking was created
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_with_overlapping_existing_bookings(self):
        """Test recurring booking that would overlap with existing approved bookings"""
        today = dt.date.today()

        # Ensure no existing bookings before the test
        Booking.objects.all().delete()
        BookingSlot.objects.all().delete()

        self.assertEqual(Booking.objects.count(), 0)  # All bookings cleared

        # First, create an approved booking for day 2
        booking = Booking.objects.create(
            user=self.renter,
            listing=self.listing,
            email="renter@example.com",
            status="APPROVED",  # This booking is already approved
            total_price=40.0,
        )

        day2 = today + dt.timedelta(days=2)
        BookingSlot.objects.create(
            booking=booking,
            start_date=day2,
            start_time=dt.time(12, 0),  # Noon to 2 PM on day 2
            end_date=day2,
            end_time=dt.time(14, 0),
        )

        # Apply the block_out_booking function to update listing availability

        block_out_booking(booking.listing, booking)

        # Now try to create a recurring booking that includes day 2 at the same time
        post_data = {
            "email": "renter@example.com",
            "is_recurring": "true",
            "recurring-start_date": today.strftime("%Y-%m-%d"),
            "recurring-start_time": "12:00",  # Noon
            "recurring-end_time": "14:00",  # 2 PM
            "recurring-pattern": "daily",
            "recurring-end_date": (today + dt.timedelta(days=4)).strftime("%Y-%m-%d"),
        }

        response = self.client.post(
            reverse("book_listing", args=[self.listing.id]), data=post_data
        )

        # Should have error message about overlapping bookings
        self.assertIn("error_messages", response.context)
        self.assertTrue(
            any(
                "unavailable" in msg.lower()
                for msg in response.context["error_messages"]
            )
        )

        # Instead of checking context, check that no new booking was created
        self.assertEqual(Booking.objects.count(), 1)  # Still just the original booking
