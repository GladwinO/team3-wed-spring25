from datetime import datetime, date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import ListingForm
from ..models import Listing, ListingSlot
from ..views import simplify_location


class ListingViewsTests(TestCase):
    def setUp(self):
        # Create a test user and log in.
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.login(username="testuser", password="testpass")

        # Create a sample listing for tests that require an existing listing.
        self.listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="Test Location [12.34, 56.78]",
            rent_per_hour=Decimal("10.00"),
            description="A test listing.",
        )
        # Create a listing slot for the sample listing.
        ListingSlot.objects.create(
            listing=self.listing,
            start_date="2025-03-12",
            start_time="10:00",
            end_date="2025-03-12",
            end_time="12:00",
        )

    def _build_slot_formset_data(self, prefix="form", count=1, slot_data=None):
        """
        Helper method to build valid formset data for ListingSlotFormSet.
        Optionally override default slot data.
        """
        data = {
            f"{prefix}-TOTAL_FORMS": str(count),
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }
        # For one slot form, use default values (can be overridden)
        if count >= 1:
            default_data = {
                f"{prefix}-0-start_date": "2025-03-12",
                f"{prefix}-0-start_time": "10:00",
                f"{prefix}-0-end_date": "2025-03-12",
                f"{prefix}-0-end_time": "12:00",
            }
            if slot_data:
                default_data.update(slot_data)
            data.update(default_data)
        return data

    def test_create_listing_get(self):
        url = reverse("create_listing")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/create_listing.html")
        self.assertIsInstance(response.context["form"], ListingForm)
        self.assertIn("slot_formset", response.context)

    def test_create_listing_view_post(self):
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        listing_data = {
            "title": "New Listing",
            "description": "New Description",
            "rent_per_hour": "15.00",
            "location": "New Location [123, 456]",
        }
        # Build slot formset data using tomorrow's date and desired times.
        slot_data = {
            "form-0-start_date": tomorrow.strftime("%Y-%m-%d"),
            "form-0-start_time": "09:00",
            "form-0-end_date": tomorrow.strftime("%Y-%m-%d"),
            "form-0-end_time": "17:00",
        }
        formset_data = self._build_slot_formset_data(
            prefix="form", count=1, slot_data=slot_data
        )
        # Note: Do not include non-existent fields such as available_from/available_until.
        post_data = {**listing_data, **formset_data}

        response = self.client.post(reverse("create_listing"), post_data)
        if response.status_code != 302:
            print("Listing form errors:", response.context["form"].errors)
            print("Slot formset errors:", response.context.get("slot_formset").errors)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("view_listings"))
        self.assertTrue(Listing.objects.filter(title="New Listing").exists())
        # Verify that the new listing has a slot with the correct start date and time.
        new_listing = Listing.objects.get(title="New Listing")
        slot = new_listing.slots.first()
        self.assertEqual(
            slot.start_date.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")
        )
        self.assertEqual(slot.start_time.strftime("%H:%M"), "09:00")

    def test_edit_listing_view_get(self):
        url = reverse("edit_listing", args=[self.listing.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/edit_listing.html")
        self.assertIsInstance(response.context["form"], ListingForm)
        self.assertIn("slot_formset", response.context)

    def test_edit_listing_view_post(self):
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        listing_data = {
            "title": "Updated Listing",
            "description": "Updated Description",
            "rent_per_hour": "20.00",
            "location": "Updated Location [123, 456]",
        }
        # For editing, include the ID of the existing slot.
        slot = self.listing.slots.first()
        slot_data = {
            "form-0-id": str(slot.id),
            "form-0-start_date": tomorrow.strftime("%Y-%m-%d"),
            "form-0-start_time": "09:00",
            "form-0-end_date": tomorrow.strftime("%Y-%m-%d"),
            "form-0-end_time": "17:00",
        }
        formset_data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        formset_data.update(slot_data)
        post_data = {**listing_data, **formset_data}
        response = self.client.post(
            reverse("edit_listing", args=[self.listing.id]), post_data
        )
        if response.status_code != 302:
            print("Listing form errors:", response.context["form"].errors)
            print("Slot formset errors:", response.context.get("slot_formset").errors)
        self.assertRedirects(response, reverse("manage_listings"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Updated Listing")
        updated_slot = self.listing.slots.first()
        self.assertEqual(
            updated_slot.start_date.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")
        )
        self.assertEqual(updated_slot.start_time.strftime("%H:%M"), "09:00")

    def test_delete_listing_view_get(self):
        url = reverse("delete_listing", args=[self.listing.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/confirm_delete.html")

    def test_delete_listing_view_post(self):
        url = reverse("delete_listing", args=[self.listing.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("manage_listings"))
        self.assertFalse(Listing.objects.filter(id=self.listing.id).exists())

    def test_listing_reviews_view(self):
        url = reverse("listing_reviews", args=[self.listing.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/listing_reviews.html")
        self.assertIn("reviews", response.context)


class ListingsFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        # Set a fixed test date for filtering
        self.test_date = date(2025, 3, 15)

        # Mock the current datetime to be 13:00 on test_date
        # This ensures our "future time" tests work consistently
        self.current_datetime = datetime.combine(self.test_date, time(13, 0))

        # Patch datetime.now() to return our fixed time
        from unittest.mock import patch

        self.datetime_patcher = patch("listings.views.datetime")
        self.mock_datetime = self.datetime_patcher.start()
        self.mock_datetime.now.return_value = self.current_datetime
        # Make sure strptime and combine still work
        self.mock_datetime.strptime = datetime.strptime
        self.mock_datetime.combine = datetime.combine

    def tearDown(self):
        # Stop patching datetime
        self.datetime_patcher.stop()

    def test_listing_time_filtering_single_interval(self):
        # Create listings with associated slots.

        # 1. Future Listing – slot from test_date 09:00 to (test_date+5 days) 17:00
        future_listing = Listing.objects.create(
            user=self.user,
            title="Future Listing",
            location="Future Location",
            rent_per_hour=10.0,
            description="This should be included",
        )
        ListingSlot.objects.create(
            listing=future_listing,
            start_date=self.test_date,
            start_time=time(9, 0),
            end_date=self.test_date + timedelta(days=5),
            end_time=time(17, 0),
        )

        # 2. Today with future time – slot from test_date 14:00 to 18:00
        today_future = Listing.objects.create(
            user=self.user,
            title="Today Future Time",
            location="Today Location",
            rent_per_hour=10.0,
            description="This should be included",
        )
        ListingSlot.objects.create(
            listing=today_future,
            start_date=self.test_date,
            start_time=time(14, 0),
            end_date=self.test_date,
            end_time=time(18, 0),
        )

        # 3. Today with past time – slot from test_date 09:00 to 12:00
        today_past = Listing.objects.create(
            user=self.user,
            title="Today Past Time",
            location="Today Past Location",
            rent_per_hour=10.0,
            description="This should be excluded",
        )
        ListingSlot.objects.create(
            listing=today_past,
            start_date=self.test_date,
            start_time=time(9, 0),
            end_date=self.test_date,
            end_time=time(12, 0),
        )

        # Apply single continuous interval filter
        url = reverse("view_listings")
        params = {
            "filter_type": "single",
            "start_date": self.test_date.strftime("%Y-%m-%d"),
            "end_date": self.test_date.strftime("%Y-%m-%d"),
            "start_time": "14:00",
            "end_time": "15:00",
        }
        response = self.client.get(url, params)
        context_listings = response.context["listings"]
        listing_titles = [listing.title for listing in context_listings]

        self.assertIn("Future Listing", listing_titles)
        self.assertIn("Today Future Time", listing_titles)
        self.assertNotIn("Today Past Time", listing_titles)
        self.assertEqual(len(listing_titles), 2)

    def test_listing_time_filtering_multiple_intervals(self):
        # Create a listing with two slots that together cover 10:00 to 16:00 on test_date.
        multi_listing = Listing.objects.create(
            user=self.user,
            title="Multi Interval Listing",
            location="Multi Location",
            rent_per_hour=15.0,
            description="This listing has multiple intervals",
        )
        ListingSlot.objects.create(
            listing=multi_listing,
            start_date=self.test_date,
            start_time=time(10, 0),
            end_date=self.test_date,
            end_time=time(13, 0),
        )
        ListingSlot.objects.create(
            listing=multi_listing,
            start_date=self.test_date,
            start_time=time(13, 0),
            end_date=self.test_date,
            end_time=time(16, 0),
        )

        url = reverse("view_listings")
        params = {
            "filter_type": "multiple",
            "interval_count": "2",
            "start_date_1": self.test_date.strftime("%Y-%m-%d"),
            "end_date_1": self.test_date.strftime("%Y-%m-%d"),
            "start_time_1": "10:00",
            "end_time_1": "12:00",
            "start_date_2": self.test_date.strftime("%Y-%m-%d"),
            "end_date_2": self.test_date.strftime("%Y-%m-%d"),
            "start_time_2": "14:00",
            "end_time_2": "15:00",
        }
        response = self.client.get(url, params)
        context_listings = response.context["listings"]
        listing_titles = [listing.title for listing in context_listings]
        # Listing should cover both intervals.
        self.assertIn("Multi Interval Listing", listing_titles)

        # Now change the second interval so it is not covered.
        params["start_time_2"] = "15:30"
        params["end_time_2"] = "16:30"
        response = self.client.get(url, params)
        context_listings = response.context["listings"]
        listing_titles = [listing.title for listing in context_listings]
        self.assertNotIn("Multi Interval Listing", listing_titles)


class ListingOwnerBookingTest(TestCase):
    def setUp(self):
        # Create two users: owner and non-owner.
        self.owner = User.objects.create_user(username="owner", password="ownerpass123")
        self.non_owner = User.objects.create_user(
            username="renter", password="renterpass123"
        )

        # Create a listing owned by the owner.
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            location="Test Location [123.456, 789.012]",
            rent_per_hour=10.0,
            description="Test Description",
        )
        # Create a slot for the listing.
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=(datetime.now() - timedelta(days=1)).date(),
            start_time=time(9, 0),
            end_date=(datetime.now() + timedelta(days=30)).date(),
            end_time=time(17, 0),
        )
        self.view_listings_url = reverse("view_listings")

    def test_owner_sees_badge_not_book_button(self):
        """Owners should see a badge (not a 'Book Now' button)."""
        self.client.login(username="owner", password="ownerpass123")
        response = self.client.get(self.view_listings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your listing")
        self.assertContains(response, 'class="badge bg-secondary"')
        book_url = reverse("book_listing", args=[self.listing.id])
        self.assertNotContains(response, f'href="{book_url}"')
        self.assertNotContains(response, "Book Now")

    def test_non_owner_sees_book_button(self):
        """Non-owners should see the 'Book Now' button."""
        self.client.login(username="renter", password="renterpass123")
        response = self.client.get(self.view_listings_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Your listing")
        book_url = reverse("book_listing", args=[self.listing.id])
        self.assertContains(response, f'href="{book_url}"')
        self.assertContains(response, 'class="btn btn-primary')
        self.assertContains(response, "Book Now")


class SimplifyLocationTest(TestCase):
    def test_simplify_location_with_institution(self):
        # For educational institutions, the full building name is retained.
        loc = (
            "Tandon School of Engineering, Johnson Street, Downtown Brooklyn, Brooklyn"
        )
        simplified = simplify_location(loc)
        self.assertEqual(simplified, "Tandon School of Engineering, Brooklyn")

    def test_simplify_location_non_institution(self):
        # For non-institution addresses, the first two parts plus the city are used.
        loc = "Some Building, Some Street, Manhattan, Extra Info"
        simplified = simplify_location(loc)
        self.assertEqual(simplified, "Some Building, Some Street, Manhattan")

    def test_simplify_location_empty(self):
        simplified = simplify_location("")
        self.assertEqual(simplified, "")


class RecurringFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        # Set a fixed test date for filtering
        self.test_date = date(2025, 3, 15)  # A Saturday

    # def test_daily_recurring_filter(self):
    #     # Create a listing available every day for a week
    #     daily_listing = Listing.objects.create(
    #         user=self.user,
    #         title="Daily Available Listing",
    #         location="Daily Location",
    #         rent_per_hour=15.0,
    #         description="Available every day from 10:00-14:00",
    #     )

    #     # Create slots for 5 consecutive days
    #     for i in range(5):
    #         current_date = self.test_date + timedelta(days=i)
    #         ListingSlot.objects.create(
    #             listing=daily_listing,
    #             start_date=current_date,
    #             start_time=time(10, 0),
    #             end_date=current_date,
    #             end_time=time(14, 0),
    #         )

    #     # Create another listing with gaps in availability
    #     partial_listing = Listing.objects.create(
    #         user=self.user,
    #         title="Partial Available Listing",
    #         location="Partial Location",
    #         rent_per_hour=20.0,
    #         description="Not available every day",
    #     )

    #     # Create slots for days 0, 2, 4 (skipping days 1 and 3)
    #     for i in range(0, 5, 2):
    #         current_date = self.test_date + timedelta(days=i)
    #         ListingSlot.objects.create(
    #             listing=partial_listing,
    #             start_date=current_date,
    #             start_time=time(10, 0),
    #             end_date=current_date,
    #             end_time=time(14, 0),
    #         )

    #     # Apply daily recurring filter for 3 consecutive days
    #     url = reverse("view_listings")
    #     params = {
    #         "filter_type": "recurring",
    #         "recurring_pattern": "daily",
    #         "recurring_start_date": self.test_date.strftime("%Y-%m-%d"),
    #         "recurring_end_date": (self.test_date + timedelta(days=2)).strftime(
    #             "%Y-%m-%d"
    #         ),
    #         "recurring_start_time": "11:00",
    #         "recurring_end_time": "13:00",
    #     }

    #     response = self.client.get(url, params)
    #     context_listings = response.context["listings"]
    #     listing_titles = [listing.title for listing in context_listings]

    #     # Daily listing should be included, partial listing should be excluded
    #     self.assertIn("Daily Available Listing", listing_titles)
    #     self.assertNotIn("Partial Available Listing", listing_titles)

    def test_weekly_recurring_filter(self):
        # Create a listing available same day every week
        weekly_listing = Listing.objects.create(
            user=self.user,
            title="Weekly Available Listing",
            location="Weekly Location",
            rent_per_hour=25.0,
            description="Available every Saturday",
        )

        # Create slots for 4 consecutive Saturdays
        for i in range(0, 28, 7):  # 0, 7, 14, 21 - four Saturdays
            current_date = self.test_date + timedelta(days=i)
            ListingSlot.objects.create(
                listing=weekly_listing,
                start_date=current_date,
                start_time=time(9, 0),
                end_date=current_date,
                end_time=time(17, 0),
            )

        # Create another listing with inconsistent weekly availability
        inconsistent_listing = Listing.objects.create(
            user=self.user,
            title="Inconsistent Weekly Listing",
            location="Inconsistent Location",
            rent_per_hour=30.0,
            description="Missing some Saturdays",
        )

        # Create slots for 1st and 3rd Saturdays only (missing 2nd and 4th)
        for i in range(0, 28, 14):  # 0, 14 - two Saturdays
            current_date = self.test_date + timedelta(days=i)
            ListingSlot.objects.create(
                listing=inconsistent_listing,
                start_date=current_date,
                start_time=time(9, 0),
                end_date=current_date,
                end_time=time(17, 0),
            )

            # NEW: Create a listing available every week but at wrong time
        wrong_time_listing = Listing.objects.create(
            user=self.user,
            title="Wrong Time Weekly Listing",
            location="Wrong Time Location",
            rent_per_hour=35.0,
            description="Available every Saturday but outside requested hours",
        )

        # Create slots for 4 consecutive Saturdays but only from 6-8am and 18-20pm
        for i in range(0, 28, 7):
            current_date = self.test_date + timedelta(days=i)
            # Morning slot (too early)
            ListingSlot.objects.create(
                listing=wrong_time_listing,
                start_date=current_date,
                start_time=time(6, 0),
                end_date=current_date,
                end_time=time(8, 0),
            )
            # Evening slot (too late)
            ListingSlot.objects.create(
                listing=wrong_time_listing,
                start_date=current_date,
                start_time=time(18, 0),
                end_date=current_date,
                end_time=time(20, 0),
            )

        # Apply weekly recurring filter for 3 weeks
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "weekly",
            "recurring_start_date": self.test_date.strftime("%Y-%m-%d"),
            "recurring_weeks": "3",
            "recurring_start_time": "10:00",
            "recurring_end_time": "16:00",
        }

        response = self.client.get(url, params)
        context_listings = response.context["listings"]
        listing_titles = [listing.title for listing in context_listings]

        # Weekly listing should be included
        self.assertIn("Weekly Available Listing", listing_titles)

        # Both inconsistent pattern and wrong time listings should be excluded
        self.assertNotIn("Inconsistent Weekly Listing", listing_titles)
        self.assertNotIn("Wrong Time Weekly Listing", listing_titles)

    # def test_overnight_recurring_filter(self):
    #     # Create a listing available for overnight stays (24/7)
    #     overnight_listing = Listing.objects.create(
    #         user=self.user,
    #         title="Overnight Listing",
    #         location="Overnight Location",
    #         rent_per_hour=40.0,
    #         description="Available for overnight stays",
    #     )

    #     # Create slots for 3 consecutive days (to cover 2 nights)
    #     for i in range(3):
    #         current_date = self.test_date + timedelta(days=i)
    #         ListingSlot.objects.create(
    #             listing=overnight_listing,
    #             start_date=current_date,
    #             start_time=time(0, 0),  # Available all day
    #             end_date=current_date,
    #             end_time=time(23, 59),
    #         )

    #     # Create a listing that's only available during daytime hours
    #     daytime_listing = Listing.objects.create(
    #         user=self.user,
    #         title="Daytime Only Listing",
    #         location="Daytime Location",
    #         rent_per_hour=30.0,
    #         description="Only available during daytime hours",
    #     )

    #     # Create daytime-only slots for the same 3 consecutive days
    #     for i in range(3):
    #         current_date = self.test_date + timedelta(days=i)
    #         ListingSlot.objects.create(
    #             listing=daytime_listing,
    #             start_date=current_date,
    #             start_time=time(9, 0),  # Available from 9am
    #             end_date=current_date,
    #             end_time=time(17, 0),  # Until 5pm
    #         )

    #     # Apply overnight recurring filter
    #     url = reverse("view_listings")
    #     params = {
    #         "filter_type": "recurring",
    #         "recurring_pattern": "daily",
    #         "recurring_start_date": self.test_date.strftime("%Y-%m-%d"),
    #         "recurring_end_date": (self.test_date + timedelta(days=1)).strftime(
    #             "%Y-%m-%d"
    #         ),
    #         "recurring_start_time": "22:00",
    #         "recurring_end_time": "08:00",  # End time is before start time, requiring overnight
    #         "recurring_overnight": "on",
    #     }

    #     response = self.client.get(url, params)
    #     context_listings = response.context["listings"]
    #     listing_titles = [listing.title for listing in context_listings]

    #     # Overnight listing should be included
    #     self.assertIn("Overnight Listing", listing_titles)
    #     # Daytime-only listing should NOT be included
    #     self.assertNotIn("Daytime Only Listing", listing_titles)

    def test_start_time_after_end_time_validation(self):
        # Apply filter with start time after end time without overnight option
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "daily",
            "recurring_start_date": self.test_date.strftime("%Y-%m-%d"),
            "recurring_end_date": self.test_date.strftime("%Y-%m-%d"),
            "recurring_start_time": "14:00",
            "recurring_end_time": "12:00",  # End time before start time
        }

        response = self.client.get(url, params)

        # Should get an error message
        self.assertIn(
            "Start time must be before end time unless overnight booking is selected",
            response.context["error_messages"],
        )
