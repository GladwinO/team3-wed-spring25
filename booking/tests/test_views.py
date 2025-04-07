import datetime as dt

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from listings.models import Listing, ListingSlot, Review
from booking.models import Booking, BookingSlot

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
