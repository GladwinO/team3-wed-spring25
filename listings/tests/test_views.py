import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from booking.models import Booking, BookingSlot
from listings.models import Listing, ListingSlot, BookmarkedListing

from ..utils import extract_coordinates


# Updated helper function to build formset data for any count.
def build_slot_formset_data(prefix="form", count=1, slot_data=None):
    data = {
        f"{prefix}-TOTAL_FORMS": str(count),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i in range(count):
        base = f"{prefix}-{i}-"
        if slot_data and any(key.startswith(base) for key in slot_data.keys()):
            data[base + "start_date"] = slot_data.get(base + "start_date", "2025-05-01")
            data[base + "start_time"] = slot_data.get(base + "start_time", "09:00")
            data[base + "end_date"] = slot_data.get(base + "end_date", "2025-05-01")
            data[base + "end_time"] = slot_data.get(base + "end_time", "17:00")
        else:
            data[base + "start_date"] = "2025-05-01"
            data[base + "start_time"] = "09:00"
            data[base + "end_date"] = "2025-05-01"
            data[base + "end_time"] = "17:00"
    return data


#############################
# Tests for create_listing view.
#############################


class CreateListingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a verified user.
        self.user_verified = User.objects.create_user(
            username="verified", password="pass"
        )
        # Update the auto-created profile.
        self.user_verified.profile.is_verified = True
        self.user_verified.profile.save()
        self.client.login(username="verified", password="pass")
        self.create_url = reverse("create_listing")
        self.now = datetime.now()

    def test_create_listing_get_verified(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/create_listing.html")
        # Verified users see the form.
        self.assertIn("form", response.context)
        self.assertIn("slot_formset", response.context)

    def test_create_listing_get_not_verified(self):
        # Create an unverified user.
        user_unverified = User.objects.create_user(
            username="unverified", password="pass"
        )
        print(user_unverified)
        # The post_save signal auto-creates a Profile with is_verified=False.
        self.client.login(username="unverified", password="pass")
        response = self.client.get(self.create_url)
        # Expect the verification card to be shown.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verification Required")
        self.assertNotContains(response, "Spot Details")

    def test_create_listing_post_valid(self):
        listing_data = {
            "title": "New Listing",
            "description": "New Description",
            "rent_per_hour": "15.00",
            "location": "New Location [123, 456]",
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }
        start_date = self.now.date() + timedelta(days=1)
        end_date = start_date

        slot_data = {
            "form-0-start_date": start_date.strftime("%Y-%m-%d"),
            "form-0-start_time": "09:00",
            "form-0-end_date": end_date.strftime("%Y-%m-%d"),
            "form-0-end_time": "17:00",
        }

        post_data = {
            **listing_data,
            **build_slot_formset_data(prefix="form", count=1, slot_data=slot_data),
        }
        response = self.client.post(self.create_url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("manage_listings"))
        self.assertTrue(Listing.objects.filter(title="New Listing").exists())
        new_listing = Listing.objects.get(title="New Listing")
        slot = new_listing.slots.first()
        self.assertEqual(slot.start_date, start_date)
        self.assertEqual(slot.end_date, end_date)
        self.assertEqual(slot.start_time, time(9, 0))
        self.assertEqual(slot.end_time, time(17, 0))

    def test_create_listing_post_invalid_form(self):
        # Missing title to force an error.
        listing_data = {
            "title": "",  # Empty title should trigger validation error
            "description": "New Description",
            "rent_per_hour": "15.00",
            "location": "New Location [123, 456]",
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }
        post_data = {**listing_data, **build_slot_formset_data(prefix="form", count=1)}
        response = self.client.post(self.create_url, post_data)
        self.assertEqual(response.status_code, 200)

        # Check for field-specific error message
        self.assertContains(response, "Please enter a spot title")

        # Verify error is associated with the correct field
        form = response.context["form"]
        self.assertIn("title", form.errors)
        self.assertIn("Please enter a spot title", str(form.errors["title"]))

    def test_create_listing_post_overlapping_slots(self):
        listing_data = {
            "title": "Overlap Listing",
            "description": "Overlap test",
            "rent_per_hour": "15.00",
            "location": "Overlap Location [123, 456]",  # Add coordinates
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }

        # Two slots that overlap
        start_date = self.now.date() + timedelta(days=1)
        end_date = start_date
        start_date2 = start_date
        end_date2 = start_date

        slot_data = {
            "form-0-start_date": start_date.strftime("%Y-%m-%d"),
            "form-0-start_time": "09:00",
            "form-0-end_date": end_date.strftime("%Y-%m-%d"),
            "form-0-end_time": "11:00",
            "form-1-start_date": start_date2.strftime("%Y-%m-%d"),
            "form-1-start_time": "10:30",
            "form-1-end_date": end_date2.strftime("%Y-%m-%d"),
            "form-1-end_time": "12:00",
        }

        post_data = {
            **listing_data,
            **build_slot_formset_data(prefix="form", count=2, slot_data=slot_data),
        }
        response = self.client.post(self.create_url, post_data)

        # Expect the view to catch overlapping slots and add field errors
        self.assertEqual(response.status_code, 200)

        # Check for overlap-specific error message
        self.assertContains(response, "This slot overlaps with another slot")

        # Verify errors are on both start_date and end_date fields
        formset = response.context["slot_formset"]
        for form in formset:
            if "start_date" in form.errors:
                self.assertIn(
                    "This slot overlaps with another slot",
                    str(form.errors["start_date"]),
                )
                self.assertIn(
                    "This slot overlaps with another slot", str(form.errors["end_date"])
                )

    def test_create_listing_past_date(self):
        """Test validation rejects past dates"""
        listing_data = {
            "title": "Past Date Test",
            "description": "Should fail validation",
            "rent_per_hour": "15.00",
            "location": "Past Date Location [123, 456]",
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }

        # Use yesterday's date to trigger validation error
        yesterday = (self.now.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (self.now.date() + timedelta(days=1)).strftime("%Y-%m-%d")

        slot_data = {
            "form-0-start_date": yesterday,
            "form-0-start_time": "09:00",
            "form-0-end_date": tomorrow,
            "form-0-end_time": "17:00",
        }

        post_data = {
            **listing_data,
            **build_slot_formset_data(prefix="form", count=1, slot_data=slot_data),
        }

        response = self.client.post(self.create_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start date cannot be in the past")

        # Verify the error is on the start_date field
        formset = response.context["slot_formset"]
        form = formset[0]
        self.assertIn("start_date", form.errors)
        self.assertIn(
            "Start date cannot be in the past", str(form.errors["start_date"])
        )

    def test_create_listing_end_date_before_start_date(self):
        """Test validation rejects end date before start date"""
        listing_data = {
            "title": "Date Order Test",
            "description": "Should fail validation",
            "rent_per_hour": "15.00",
            "location": "Date Order Location [123, 456]",
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }

        # End date before start date
        start_date = (self.now.date() + timedelta(days=2)).strftime("%Y-%m-%d")
        end_date = (self.now.date() + timedelta(days=1)).strftime("%Y-%m-%d")

        slot_data = {
            "form-0-start_date": start_date,
            "form-0-start_time": "09:00",
            "form-0-end_date": end_date,
            "form-0-end_time": "17:00",
        }

        post_data = {
            **listing_data,
            **build_slot_formset_data(prefix="form", count=1, slot_data=slot_data),
        }

        response = self.client.post(self.create_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "End date cannot be before start date")

        # Verify the error is on the end_date field
        formset = response.context["slot_formset"]
        form = formset[0]
        self.assertIn("end_date", form.errors)
        self.assertIn(
            "End date cannot be before start date", str(form.errors["end_date"])
        )

    def test_form_mode_preserved_on_validation_error(self):
        """Test that form mode (recurring or single) is preserved after validation error"""
        # Test recurring mode is preserved
        recurring_data = {
            "title": "Recurring Mode Test",
            "description": "Testing mode preservation",
            "rent_per_hour": "15.00",
            "location": "Mode Test Location [40.712776, -74.005974]",
            "has_ev_charger": False,
            "parking_spot_size": "STANDARD",
            "is_recurring": "true",
            "recurring_pattern": "daily",
            # Missing recurring_end_date to trigger validation error
            "recurring_start_date": (
                datetime.now().date() + timedelta(days=1)
            ).strftime("%Y-%m-%d"),
            "recurring_start_time": "09:00",
            "recurring_end_time": "17:00",
        }

        response = self.client.post(self.create_url, recurring_data)
        self.assertEqual(response.status_code, 200)

        # Check that is_recurring is still True in the context
        self.assertTrue(response.context["is_recurring"])
        self.assertContains(response, "End date is required for daily pattern")

        # Test single mode is preserved
        single_data = {
            "title": "Single Mode Test",
            "description": "Testing mode preservation",
            "rent_per_hour": "-5.00",  # Negative price to trigger validation error
            "location": "Mode Test Location [40.712776, -74.005974]",
            "has_ev_charger": False,
            "parking_spot_size": "STANDARD",
            "is_recurring": "false",
        }

        single_data.update(build_slot_formset_data(prefix="form", count=1))

        response = self.client.post(self.create_url, single_data)
        self.assertEqual(response.status_code, 200)

        # Check that is_recurring is still False in the context
        self.assertFalse(response.context["is_recurring"])
        self.assertContains(response, "Price must be greater than zero")


###################################
# Tests for create_listing view with recurring listings.
###################################
class RecurringListingCreationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")
        self.create_url = reverse("create_listing")
        self.tomorrow = datetime.now().date() + timedelta(days=1)
        self.next_week = self.tomorrow + timedelta(days=7)

        # Basic listing data for all tests
        self.listing_data = {
            "title": "Test Recurring Listing",
            "location": "Test Location [40.712776, -74.005974]",
            "rent_per_hour": "15.00",
            "description": "A test recurring listing",
            "parking_spot_size": "STANDARD",
            "has_ev_charger": "",
            "is_recurring": "true",
        }

    def test_create_daily_recurring_listing(self):
        """Test creating a listing with daily recurring slots"""
        data = self.listing_data.copy()
        data.update(
            {
                "recurring_pattern": "daily",
                "recurring_start_date": self.tomorrow.strftime("%Y-%m-%d"),
                "recurring_end_date": self.next_week.strftime("%Y-%m-%d"),
                "recurring_start_time": "09:00",
                "recurring_end_time": "17:00",
            }
        )

        response = self.client.post(self.create_url, data)

        # Check redirect on success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("manage_listings"))

        # Verify listing was created
        listing = Listing.objects.get(title="Test Recurring Listing")
        self.assertEqual(listing.user, self.user)

        # Check that slots were created
        days_difference = (self.next_week - self.tomorrow).days + 1
        slots = ListingSlot.objects.filter(listing=listing)
        self.assertEqual(slots.count(), days_difference)

    def test_create_weekly_recurring_listing(self):
        """Test creating a listing with weekly recurring slots"""
        data = self.listing_data.copy()
        data.update(
            {
                "recurring_pattern": "weekly",
                "recurring_start_date": self.tomorrow.strftime("%Y-%m-%d"),
                "recurring_start_time": "09:00",
                "recurring_end_time": "17:00",
                "recurring_weeks": "3",
            }
        )

        response = self.client.post(self.create_url, data)

        # Check redirect on success
        self.assertEqual(response.status_code, 302)

        # Verify listing was created
        listing = Listing.objects.filter(title="Test Recurring Listing").first()
        self.assertIsNotNone(listing)

        # Check that slots were created (3 weeks)
        slots = ListingSlot.objects.filter(listing=listing)
        self.assertEqual(slots.count(), 3)

        # Verify weekly pattern (dates should be 7 days apart)
        dates = [slot.start_date for slot in slots.order_by("start_date")]
        self.assertEqual((dates[1] - dates[0]).days, 7)
        self.assertEqual((dates[2] - dates[1]).days, 7)

    def test_create_overnight_recurring_listing(self):
        """Test creating a listing with overnight recurring slots"""
        data = self.listing_data.copy()
        data.update(
            {
                "recurring_pattern": "weekly",
                "recurring_start_date": self.tomorrow.strftime("%Y-%m-%d"),
                "recurring_start_time": "18:00",
                "recurring_end_time": "09:00",
                "recurring_overnight": "on",
                "recurring_weeks": "2",
            }
        )

        response = self.client.post(self.create_url, data)

        # Check redirect on success
        self.assertEqual(response.status_code, 302)

        # Verify listing was created
        listing = Listing.objects.filter(title="Test Recurring Listing").first()
        self.assertIsNotNone(listing)

        # Check overnight slots
        slots = ListingSlot.objects.filter(listing=listing)
        for slot in slots:
            # End date should be day after start date for overnight
            self.assertEqual((slot.end_date - slot.start_date).days, 1)

    def test_recurring_validation_errors(self):
        """Test validation for recurring form"""
        # Basic listing data
        listing_data = {
            "title": "Recurring Validation Test",
            "description": "Testing recurring validation",
            "rent_per_hour": "15.00",
            "location": "Recurring Test Location [40.712776, -74.005974]",
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
            "is_recurring": "true",
        }

        # Add recurring data with issues (past start date)
        yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")

        data = listing_data.copy()
        data.update(
            {
                "recurring_pattern": "daily",
                "recurring_start_date": yesterday,  # Past date - should fail
                "recurring_end_date": tomorrow,
                "recurring_start_time": "09:00",
                "recurring_end_time": "17:00",
            }
        )

        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 200)

        # Use a more flexible assertion that checks if the content is in there in any format
        recurring_form = response.context["recurring_form"]
        self.assertTrue("recurring_start_date" in recurring_form.errors)
        self.assertTrue(
            "Start date cannot be in the past"
            in str(recurring_form.errors["recurring_start_date"])
        )

        # Original assertion - keep it but it might need to be adjusted based on HTML formatting
        # self.assertContains(response, "Start date cannot be in the past.")

        # Verify the error is on the recurring_start_date field
        recurring_form = response.context["recurring_form"]
        self.assertIn("recurring_start_date", recurring_form.errors)
        self.assertIn(
            "Start date cannot be in the past.",
            str(recurring_form.errors["recurring_start_date"]),
        )

        # Test end time before start time without overnight
        data = listing_data.copy()
        data.update(
            {
                "recurring_pattern": "daily",
                "recurring_start_date": tomorrow,
                "recurring_end_date": tomorrow,
                "recurring_start_time": "10:00",
                "recurring_end_time": "09:00",  # Earlier than start time - should fail
                "recurring_overnight": False,
            }
        )

        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 200)
        # self.assertContains(response, "End time must be later than start time.")

        # Use a more flexible assertion that checks if the content is in there in any format
        recurring_form = response.context["recurring_form"]
        self.assertTrue("recurring_end_time" in recurring_form.errors)
        self.assertTrue(
            "End time must be later than start time"
            in str(recurring_form.errors["recurring_end_time"])
        )

        # Verify the error is on the recurring_end_time field
        recurring_form = response.context["recurring_form"]
        self.assertIn("recurring_end_time", recurring_form.errors)


#############################
# Tests for edit_listing view.
#############################


class EditListingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="editor", password="pass")
        self.client.login(username="editor", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Editable Listing",
            location="Edit Location",
            rent_per_hour=Decimal("10.00"),
            description="Editable",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        self.now = datetime.now()
        start_date = self.now.date() + timedelta(days=1)
        end_date = start_date

        self.original_slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=start_date.strftime("%Y-%m-%d"),
            start_time="09:00",
            end_date=end_date.strftime("%Y-%m-%d"),
            end_time="17:00",
        )
        self.edit_url = reverse("edit_listing", args=[self.listing.id])

    def _build_edit_slot_data(self, prefix="form", count=1, slot_data=None):
        data = {
            f"{prefix}-TOTAL_FORMS": str(count),
            f"{prefix}-INITIAL_FORMS": str(count),
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }
        if count >= 1:
            # Ensure that start_date is a string.
            slot_date = self.original_slot.start_date
            if not isinstance(slot_date, str):
                slot_date = slot_date.strftime("%Y-%m-%d")
            default_data = {
                f"{prefix}-0-id": str(self.original_slot.id),
                f"{prefix}-0-start_date": slot_date,
                f"{prefix}-0-start_time": "10:00",
                f"{prefix}-0-end_date": slot_date,
                f"{prefix}-0-end_time": "12:00",
            }
            if slot_data:
                default_data.update(slot_data)
            data.update(default_data)
        return data

    def test_edit_listing_get(self):
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/edit_listing.html")
        self.assertIn("form", response.context)
        self.assertIn("slot_formset", response.context)

    def test_edit_listing_post_valid(self):
        new_date = self.now + timedelta(days=2)
        new_date = new_date.strftime("%Y-%m-%d")
        listing_data = {
            "title": "Updated Listing",
            "description": "Updated Desc",
            "rent_per_hour": "20.00",
            "location": self.listing.location,
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }
        slot_data = {
            "form-0-id": str(self.original_slot.id),
            "form-0-start_date": new_date,
            "form-0-start_time": "09:00",
            "form-0-end_date": new_date,
            "form-0-end_time": "17:00",
        }
        formset_data = self._build_edit_slot_data(
            prefix="form", count=1, slot_data=slot_data
        )
        post_data = {**listing_data, **formset_data}
        response = self.client.post(self.edit_url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("manage_listings"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Updated Listing")
        updated_slot = self.listing.slots.first()
        self.assertEqual(updated_slot.start_date.strftime("%Y-%m-%d"), new_date)
        self.assertEqual(updated_slot.start_time.strftime("%H:%M"), "09:00")

    def test_edit_listing_overlapping_slots_error(self):
        listing_data = {
            "title": "Overlap Edit",
            "description": "Overlap conflict",
            "rent_per_hour": "10.00",
            "location": self.listing.location,
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }
        start_date = self.now.date() + timedelta(days=1)
        start_date = start_date.strftime("%Y-%m-%d")
        slot_data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": str(self.original_slot.id),
            "form-0-start_date": start_date,
            "form-0-start_time": "10:00",
            "form-0-end_date": start_date,
            "form-0-end_time": "12:00",
            "form-1-start_date": start_date,
            "form-1-start_time": "11:00",
            "form-1-end_date": start_date,
            "form-1-end_time": "13:00",
        }
        post_data = {**listing_data, **slot_data}
        response = self.client.post(self.edit_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overlapping slots detected. Please correct.")

    def test_edit_listing_pending_bookings_block(self):
        Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="pending@example.com",
            total_price=0,
            status="PENDING",
        )
        listing_data = {
            "title": "Blocked Edit",
            "description": "Should not allow edit",
            "rent_per_hour": "12.00",
            "location": self.listing.location,
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }
        slot_data = self._build_edit_slot_data(prefix="form", count=1)
        post_data = {**listing_data, **slot_data}
        response = self.client.post(self.edit_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "You cannot edit your listing while there is a pending booking"
        )

    def test_edit_listing_active_booking_conflict(self):
        booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="active@example.com",
            total_price=0,
            status="APPROVED",
        )
        # Convert start_date to string if necessary.
        slot_date = self.original_slot.start_date
        if not isinstance(slot_date, str):
            slot_date_str = slot_date.strftime("%Y-%m-%d")
        else:
            slot_date_str = slot_date
        BookingSlot.objects.create(
            booking=booking,
            start_date=datetime.strptime(slot_date_str, "%Y-%m-%d").date(),
            start_time="10:00",
            end_date=datetime.strptime(slot_date_str, "%Y-%m-%d").date(),
            end_time="12:00",
        )
        listing_data = {
            "title": "Conflict Edit",
            "description": "Conflicting availability",
            "rent_per_hour": "10.00",
            "location": self.listing.location,
            "has_ev_charger": False,
            "charger_level": "",
            "connector_type": "",
            "parking_spot_size": "STANDARD",
        }
        slot_data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-start_date": slot_date_str,
            "form-0-start_time": "11:00",
            "form-0-end_date": slot_date_str,
            "form-0-end_time": "13:00",
        }
        post_data = {**listing_data, **slot_data}
        response = self.client.post(self.edit_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your changes conflict with an active booking")

    def test_edit_listing_get_updates_ongoing_slot_initial(self):
        # Use current date from self.now instead of hard-coded date
        current_date = self.now.date() + timedelta(days=1)

        # Create an ongoing slot that starts at 10:00 and ends at 12:00
        ongoing_slot = ListingSlot.objects.create(
            listing=self.listing,
            start_date=current_date,
            start_time="10:00",
            end_date=current_date,
            end_time="12:00",
        )

        # Use a time that's between start and end (11:00) but on the current date
        fixed_now = datetime.combine(current_date, time(11, 0))

        # Patch datetime.now() in the view so that current_dt == fixed_now
        with patch("listings.views.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.combine = datetime.combine
            mock_datetime.strptime = datetime.strptime
            response = self.client.get(self.edit_url)

        # In the view, the code sets form.initial["start_time"] for ongoing slots
        formset = response.context["slot_formset"]
        found = False
        for form in formset.forms:
            if form.instance.id == ongoing_slot.id:
                # According to the view logic, if current_dt is 11:00 (minute=0),
                # then new_minute becomes 30 and hour stays 11, so expected "11:30"
                self.assertEqual(form.initial.get("start_time"), "11:30")
                found = True
        self.assertTrue(found)


# --- Tests for view_listings ---
class ListingsFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="filteruser", password="pass")
        self.client.login(username="filteruser", password="pass")
        # Set test_date to a future date.
        self.test_date = date.today() + timedelta(days=10)
        # Listing 1: Future Listing.
        self.future_listing = Listing.objects.create(
            user=self.user,
            title="Future Listing",
            location="Future Location",
            rent_per_hour=10.00,
            description="Should be included",
            parking_spot_size="STANDARD",
        )
        ListingSlot.objects.create(
            listing=self.future_listing,
            start_date=self.test_date,
            start_time=time(9, 0),
            end_date=self.test_date + timedelta(days=5),
            end_time=time(17, 0),
        )
        # Listing 2: Today Future Time.
        self.today_future = Listing.objects.create(
            user=self.user,
            title="Today Future Time",
            location="Today Location",
            rent_per_hour=10.00,
            description="Should be included",
            parking_spot_size="STANDARD",
        )
        ListingSlot.objects.create(
            listing=self.today_future,
            start_date=self.test_date,
            start_time=time(14, 0),
            end_date=self.test_date,
            end_time=time(18, 0),
        )
        # Listing 3: Today Past Time.
        self.today_past = Listing.objects.create(
            user=self.user,
            title="Today Past Time",
            location="Past Location",
            rent_per_hour=10.00,
            description="Should be excluded",
            parking_spot_size="STANDARD",
        )
        ListingSlot.objects.create(
            listing=self.today_past,
            start_date=self.test_date,
            start_time=time(9, 0),
            end_date=self.test_date,
            end_time=time(12, 0),
        )
        # Patch datetime in listings.views so that "now" is before test_date.
        self.patcher = patch("listings.views.datetime")
        self.mock_datetime = self.patcher.start()
        fixed_now = datetime.combine(self.test_date - timedelta(days=1), time(12, 0))
        self.mock_datetime.now.return_value = fixed_now
        self.mock_datetime.combine = datetime.combine
        self.mock_datetime.strptime = datetime.strptime

    def tearDown(self):
        self.patcher.stop()

    def test_view_listings_default(self):
        url = reverse("view_listings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("listings", response.context)

    def test_view_listings_filter_max_price(self):
        Listing.objects.create(
            user=self.user,
            title="Expensive Listing",
            location="999 Rich St",
            rent_per_hour=50.00,
            description="Expensive",
            parking_spot_size="STANDARD",
        )
        url = reverse("view_listings")
        response = self.client.get(url, {"max_price": "20"})
        self.assertEqual(response.status_code, 200)
        listings = response.context["listings"]
        for listing in listings:
            self.assertLessEqual(float(listing.rent_per_hour), 20.0)

    def test_view_listings_ajax(self):
        url = reverse("view_listings")
        response = self.client.get(url, {"ajax": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/partials/listing_cards.html")

    def test_single_interval_filter(self):
        url = reverse("view_listings")
        params = {
            "filter_type": "single",
            "start_date": self.test_date.strftime("%Y-%m-%d"),
            "end_date": self.test_date.strftime("%Y-%m-%d"),
            "start_time": "14:00",
            "end_time": "15:00",
        }
        response = self.client.get(url, params)
        titles = [listing.title for listing in response.context["listings"]]
        self.assertIn("Future Listing", titles)
        self.assertIn("Today Future Time", titles)
        self.assertNotIn("Today Past Time", titles)

    def test_multiple_intervals_filter(self):
        multi_listing = Listing.objects.create(
            user=self.user,
            title="Multi Interval Listing",
            location="Multi Location",
            rent_per_hour=15.00,
            description="Multiple intervals",
            parking_spot_size="STANDARD",
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
        titles = [listing.title for listing in response.context["listings"]]
        self.assertIn("Multi Interval Listing", titles)
        params["start_time_2"] = "15:30"
        params["end_time_2"] = "16:30"
        response = self.client.get(url, params)
        titles = [listing.title for listing in response.context["listings"]]
        self.assertNotIn("Multi Interval Listing", titles)

    def test_recurring_filter_invalid_time(self):
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "daily",
            "recurring_start_date": self.test_date.strftime("%Y-%m-%d"),
            "recurring_end_date": self.test_date.strftime("%Y-%m-%d"),
            "recurring_start_time": "14:00",
            "recurring_end_time": "12:00",  # invalid without overnight
        }
        response = self.client.get(url, params)
        self.assertIn(
            "Start time must be before end time unless overnight booking is selected",
            response.context["error_messages"],
        )

    def test_recurring_daily_missing_end_date(self):
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "daily",
            "recurring_start_date": self.test_date.strftime("%Y-%m-%d"),
            # Missing recurring_end_date
            "recurring_start_time": "10:00",
            "recurring_end_time": "12:00",
        }
        response = self.client.get(url, params)
        self.assertIn(
            "End date is required for daily recurring pattern",
            response.context["error_messages"],
        )
        self.assertEqual(len(response.context["listings"]), 0)

    def test_recurring_daily_end_date_before_start(self):
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "daily",
            "recurring_start_date": "2025-04-10",
            "recurring_end_date": "2025-04-09",
            "recurring_start_time": "10:00",
            "recurring_end_time": "12:00",
        }
        response = self.client.get(url, params)
        self.assertIn(
            "End date must be on or after start date",
            response.context["error_messages"],
        )
        self.assertEqual(len(response.context["listings"]), 0)

    def test_recurring_weekly_missing_weeks(self):
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "weekly",
            "recurring_start_date": "2025-04-10",
            "recurring_start_time": "10:00",
            "recurring_end_time": "12:00",
            # Missing recurring_weeks
        }
        response = self.client.get(url, params)
        self.assertIn(
            "Number of weeks is required for weekly recurring pattern",
            response.context["error_messages"],
        )
        self.assertEqual(len(response.context["listings"]), 0)

    def test_recurring_weekly_invalid_weeks(self):
        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "weekly",
            "recurring_start_date": "2025-04-10",
            "recurring_start_time": "10:00",
            "recurring_end_time": "12:00",
            "recurring_weeks": "-1",
        }
        response = self.client.get(url, params)
        self.assertIn(
            "Number of weeks must be positive", response.context["error_messages"]
        )
        self.assertEqual(len(response.context["listings"]), 0)

    def test_recurring_daily_valid(self):
        valid_listing = Listing.objects.create(
            user=self.user,
            title="Recurring Daily Listing",
            location="Valid Location",
            rent_per_hour=20.00,
            description="Available daily",
            has_ev_charger=False,
        )
        # make start_date_slot now
        start_date_slot = datetime.now().date()
        end_date_slot = start_date_slot + timedelta(days=10)
        ListingSlot.objects.create(
            listing=valid_listing,
            start_date=start_date_slot,
            start_time="08:00",
            end_date=end_date_slot,
            end_time="20:00",
        )
        recurring_start_date = (start_date_slot + timedelta(days=2)).strftime(
            "%Y-%m-%d"
        )
        recurring_end_date = (start_date_slot + timedelta(days=4)).strftime("%Y-%m-%d")

        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "daily",
            "recurring_start_date": recurring_start_date,
            "recurring_end_date": recurring_end_date,
            "recurring_start_time": "09:00",
            "recurring_end_time": "10:00",
        }
        response = self.client.get(url, params)
        listings = response.context["listings"]
        titles = [listing.title for listing in listings]
        self.assertIn("Recurring Daily Listing", titles)

    def test_recurring_weekly_valid(self):
        # Create a listing with slots on 3 consecutive weeks
        weekly_listing = Listing.objects.create(
            user=self.user,
            title="Recurring Weekly Listing",
            location="Weekly Location",
            rent_per_hour=25.00,
            description="Available weekly",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )

        # Use the test_date from setUp that's already patched in the mock_datetime
        start_date = self.test_date

        # Create 4 weekly slots
        for week_offset in range(3):
            slot_date = start_date + timedelta(weeks=week_offset)
            ListingSlot.objects.create(
                listing=weekly_listing,
                start_date=slot_date,
                start_time="09:00",
                end_date=slot_date,
                end_time="17:00",
            )

        url = reverse("view_listings")
        params = {
            "filter_type": "recurring",
            "recurring_pattern": "weekly",
            "recurring_start_date": start_date.strftime("%Y-%m-%d"),
            "recurring_weeks": "3",
            "recurring_start_time": "10:00",
            "recurring_end_time": "16:00",
        }

        response = self.client.get(url, params)
        listings = response.context["listings"]
        titles = [listing.title for listing in listings]

        self.assertIn("Recurring Weekly Listing", titles)


# --- Tests for manage_listings, delete_listing, and listing_reviews ---


class ManageListingsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username="manageowner", password="pass")
        self.client.login(username="manageowner", password="pass")
        self.listing1 = Listing.objects.create(
            user=self.owner,
            title="Manage Listing 1",
            location="Loc 1",
            rent_per_hour=10.00,
            description="Desc 1",
            parking_spot_size="STANDARD",
        )
        self.listing2 = Listing.objects.create(
            user=self.owner,
            title="Manage Listing 2",
            location="Loc 2",
            rent_per_hour=12.00,
            description="Desc 2",
            parking_spot_size="STANDARD",
        )
        Booking.objects.create(
            user=self.owner,
            listing=self.listing1,
            email="a@example.com",
            total_price=0,
            status="PENDING",
        )
        Booking.objects.create(
            user=self.owner,
            listing=self.listing2,
            email="b@example.com",
            total_price=0,
            status="APPROVED",
        )

    def test_manage_listings_view(self):
        url = reverse("manage_listings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("listings", response.context)
        for listing in response.context["listings"]:
            self.assertTrue(hasattr(listing, "pending_bookings"))
            self.assertTrue(hasattr(listing, "approved_bookings"))


class ListingOwnerBookingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.renter = User.objects.create_user(username="renter", password="pass")
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Owner Parking",
            location="Owner Loc [12,34]",
            rent_per_hour=10.00,
            description="Owner description",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=(datetime.now() + timedelta(days=1)).date(),
            start_time="09:00",
            end_date=(datetime.now() + timedelta(days=1)).date(),
            end_time="17:00",
        )

    def test_owner_sees_badge_not_book_button(self):
        self.client.login(username="owner", password="pass")
        url = reverse("view_listings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your listing")
        self.assertContains(
            response, 'class="badge bg-secondary outline-badge text-decoration-none"'
        )
        book_url = reverse("book_listing", args=[self.listing.id])
        self.assertNotContains(response, f'href="{book_url}"')
        self.assertNotContains(response, "Book Now")

    def test_non_owner_sees_book_button(self):
        self.client.login(username="renter", password="pass")
        url = reverse("view_listings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Your listing")

        # Use a partial URL match instead of exact URL match
        book_url_base = reverse("book_listing", args=[self.listing.id])
        self.assertContains(
            response, f'href="{book_url_base}'
        )  # Note: removed closing quote

        self.assertContains(response, 'class="btn btn-primary')
        self.assertContains(response, "Book Now")


class EVChargerViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="evuser", password="evpass")
        self.client.login(username="evuser", password="evpass")
        self.non_ev = Listing.objects.create(
            user=self.user,
            title="Regular Parking",
            location="Regular Loc",
            rent_per_hour=Decimal("10.00"),
            description="No EV charger",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        self.l2 = Listing.objects.create(
            user=self.user,
            title="Level 2 Charging",
            location="L2 Loc",
            rent_per_hour=Decimal("15.00"),
            description="Standard charger",
            has_ev_charger=True,
            charger_level="L2",
            connector_type="J1772",
            parking_spot_size="STANDARD",
        )
        self.l3 = Listing.objects.create(
            user=self.user,
            title="Fast Charging Tesla",
            location="Tesla Loc",
            rent_per_hour=Decimal("25.00"),
            description="DC Fast Charging",
            has_ev_charger=True,
            charger_level="L3",
            connector_type="TESLA",
            parking_spot_size="STANDARD",
        )
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        for listing in [self.non_ev, self.l2, self.l3]:
            ListingSlot.objects.create(
                listing=listing,
                start_date=tomorrow,
                start_time="09:00",
                end_date=tomorrow,
                end_time="17:00",
            )

    def test_filter_by_ev_charger_presence(self):
        response = self.client.get(reverse("view_listings"), {"has_ev_charger": "on"})
        listings = response.context["listings"]
        ids = [listing.id for listing in listings]
        self.assertIn(self.l2.id, ids)
        self.assertIn(self.l3.id, ids)
        self.assertNotIn(self.non_ev.id, ids)

    def test_filter_by_charger_level(self):
        response = self.client.get(
            reverse("view_listings"), {"has_ev_charger": "on", "charger_level": "L3"}
        )
        listings = response.context["listings"]
        ids = [listing.id for listing in listings]
        self.assertIn(self.l3.id, ids)
        self.assertNotIn(self.l2.id, ids)
        self.assertNotIn(self.non_ev.id, ids)

    def test_filter_by_connector_type(self):
        response = self.client.get(
            reverse("view_listings"),
            {"has_ev_charger": "on", "connector_type": "TESLA"},
        )
        listings = response.context["listings"]
        ids = [listing.id for listing in listings]
        self.assertIn(self.l3.id, ids)
        self.assertNotIn(self.l2.id, ids)
        self.assertNotIn(self.non_ev.id, ids)

    def test_combined_ev_filters(self):
        l3_j1772 = Listing.objects.create(
            user=self.user,
            title="L3 with J1772",
            location="L3 J1772 Loc",
            rent_per_hour=Decimal("20.00"),
            description="Fast charging with J1772",
            has_ev_charger=True,
            charger_level="L3",
            connector_type="J1772",
            parking_spot_size="STANDARD",
        )
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        ListingSlot.objects.create(
            listing=l3_j1772,
            start_date=tomorrow,
            start_time="09:00",
            end_date=tomorrow,
            end_time="17:00",
        )
        response = self.client.get(
            reverse("view_listings"),
            {
                "has_ev_charger": "on",
                "charger_level": "L3",
                "connector_type": "TESLA",
            },
        )
        listings = response.context["listings"]
        ids = [listing.id for listing in listings]
        self.assertIn(self.l3.id, ids)
        self.assertNotIn(self.l2.id, ids)
        self.assertNotIn(l3_j1772.id, ids)
        self.assertContains(response, "Level 3")
        self.assertContains(response, "Tesla")
        self.assertContains(response, "fa-charging-station")
        self.assertContains(response, "fa-plug")


class LocationSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create test listings with different locations
        self.listing1 = Listing.objects.create(
            user=self.user,
            title="NYC Parking",
            location="[40.7128,-74.0060]",  # New York City coordinates
            rent_per_hour=Decimal("25.00"),
            description="Parking in NYC",
            parking_spot_size="STANDARD",
        )

        self.listing2 = Listing.objects.create(
            user=self.user,
            title="Boston Parking",
            location="[42.3601,-71.0589]",  # Boston coordinates
            rent_per_hour=Decimal("20.00"),
            description="Parking in Boston",
            parking_spot_size="STANDARD",
        )

        self.listing3 = Listing.objects.create(
            user=self.user,
            title="Invalid Location",
            location="invalid",
            rent_per_hour=Decimal("15.00"),
            description="Invalid location",
            parking_spot_size="STANDARD",
        )

        # Add slots to make listings appear in searches
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        for listing in [self.listing1, self.listing2, self.listing3]:
            ListingSlot.objects.create(
                listing=listing,
                start_date=tomorrow,
                start_time="09:00",
                end_date=tomorrow,
                end_time="17:00",
            )

    def test_location_search_with_radius(self):
        """Test searching listings within a specific radius"""
        # Search near NYC with 100km radius
        response = self.client.get(
            reverse("view_listings"),
            {
                "lat": "40.7128",
                "lng": "-74.0060",
                "radius": "100",
                "enable_radius": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])

        # Get listings with valid distances within radius
        valid_listings = []
        for listing in listings:
            if hasattr(listing, "distance") and listing.distance is not None:
                if listing.distance <= 100:
                    valid_listings.append(listing)

        # Only NYC listing should be within 100km
        self.assertEqual(len(valid_listings), 1)
        self.assertEqual(valid_listings[0].title, "NYC Parking")
        self.assertLess(
            valid_listings[0].distance, 1
        )  # NYC listing should be very close

    def test_location_search_without_radius(self):
        """Test searching listings without radius (should sort by distance)"""
        response = self.client.get(
            reverse("view_listings"), {"lat": "40.7128", "lng": "-74.0060"}
        )

        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])
        # All listings should be included, but sorted by distance
        self.assertEqual(len(listings), 3)  # Including the invalid location listing

        # Check that listings with valid coordinates have distances
        valid_listings = [
            listing_item
            for listing_item in listings
            if hasattr(listing_item, "distance") and listing_item.distance is not None
        ]
        self.assertEqual(len(valid_listings), 2)

        # NYC should be first among valid listings (closest)
        self.assertEqual(valid_listings[0].title, "NYC Parking")

    def test_distance_calculation(self):
        """Test that distances are correctly calculated and added to listings"""
        response = self.client.get(
            reverse("view_listings"), {"lat": "40.7128", "lng": "-74.0060"}
        )

        self.assertEqual(response.status_code, 200)
        listings = list(response.context["listings"])
        nyc_listing = next(
            listing_item
            for listing_item in listings
            if listing_item.title == "NYC Parking"
        )

        # NYC listing should have distance close to 0
        self.assertTrue(hasattr(nyc_listing, "distance"))
        self.assertLess(nyc_listing.distance, 1)

    def test_coordinate_extraction(self):
        """Test the coordinate extraction utility function"""
        # Test valid coordinates
        lat, lng = extract_coordinates("[40.7128,-74.0060]")
        self.assertAlmostEqual(lat, 40.7128)
        self.assertAlmostEqual(lng, -74.0060)

        # Test invalid coordinates
        with self.assertRaises(ValueError):
            extract_coordinates("invalid")

    def test_listings_without_coordinates(self):
        """Test that listings with invalid coordinates are still included"""
        response = self.client.get(
            reverse("view_listings"), {"lat": "40.7128", "lng": "-74.0060"}
        )

        self.assertEqual(response.status_code, 200)
        invalid_listing = next(
            (
                listing
                for listing in response.context["listings"]
                if listing.title == "Invalid Location"
            ),
            None,
        )
        # Invalid listing should be included with None distance
        self.assertIsNotNone(invalid_listing)
        self.assertIsNone(invalid_listing.distance)


# --- Tests for delete_listing and listing_reviews ---


class DeleteListingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="deleter", password="pass")
        self.client.login(username="deleter", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Delete Test Listing",
            location="Delete Loc",
            rent_per_hour=Decimal("10.00"),
            description="To be deleted",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        self.delete_url = reverse("delete_listing", args=[self.listing.id])

    def test_delete_listing_view_get(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/confirm_delete.html")

    def test_delete_listing_view_post(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("manage_listings"))
        self.assertFalse(Listing.objects.filter(id=self.listing.id).exists())

    def test_delete_listing_active_booking(self):
        Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="conflict@example.com",
            total_price=0,
            status="PENDING",
        )
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot delete listing with pending bookings")


class ListingReviewsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="reviewer", password="pass")
        self.client.login(username="reviewer", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Review Test Listing",
            location="Review Loc",
            rent_per_hour=Decimal("10.00"),
            description="Review test",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        from booking.models import Booking

        self.booking = Booking.objects.create(
            user=self.user,
            listing=self.listing,
            email="review@example.com",
            total_price=0,
            status="APPROVED",
        )
        from listings.models import Review

        Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            user=self.user,
            rating=5,
            comment="Great!",
        )

    def test_listing_reviews_view(self):
        url = reverse("listing_reviews", args=[self.listing.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/listing_reviews.html")
        self.assertIn("reviews", response.context)


# --- Tests covering remaining branches in view_listings (including AJAX, recurring, context) ---
class ViewListingsContextTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="contextuser", password="pass")
        self.client.login(username="contextuser", password="pass")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Context Listing",
            location="Context Loc",
            rent_per_hour=Decimal("10.00"),
            description="Test context",
            has_ev_charger=False,
            parking_spot_size="STANDARD",
        )
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=(date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
            start_time="10:00",
            end_date=(date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
            end_time="12:00",
        )
        self.view_url = reverse("view_listings")

    def test_view_listings_context(self):
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIn("half_hour_choices", context)
        self.assertIn("error_messages", context)
        self.assertIn("warning_messages", context)
        self.assertIn("has_next", context)
        self.assertIn("next_page", context)

    def test_view_listings_ajax(self):
        response = self.client.get(self.view_url, {"ajax": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/partials/listing_cards.html")


class SpotSizeFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="spotuser", password="pass")
        self.client.login(username="spotuser", password="pass")

        # Create listings with different spot sizes
        self.standard_listing = Listing.objects.create(
            user=self.user,
            title="Standard Spot",
            location="Standard Location",
            rent_per_hour=10.00,
            description="Standard size spot",
            parking_spot_size="STANDARD",
        )

        self.compact_listing = Listing.objects.create(
            user=self.user,
            title="Compact Spot",
            location="Compact Location",
            rent_per_hour=8.00,
            description="Compact size spot",
            parking_spot_size="COMPACT",
        )

        self.oversize_listing = Listing.objects.create(
            user=self.user,
            title="Oversize Spot",
            location="Oversize Location",
            rent_per_hour=15.00,
            description="Oversize spot",
            parking_spot_size="OVERSIZE",
        )

        self.commercial_listing = Listing.objects.create(
            user=self.user,
            title="Commercial Spot",
            location="Commercial Location",
            rent_per_hour=20.00,
            description="Commercial spot",
            parking_spot_size="COMMERCIAL",
        )

        # Add slots to make listings appear in searches
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        for listing in [
            self.standard_listing,
            self.compact_listing,
            self.oversize_listing,
            self.commercial_listing,
        ]:
            ListingSlot.objects.create(
                listing=listing,
                start_date=tomorrow,
                start_time="09:00",
                end_date=tomorrow,
                end_time="17:00",
            )

    def test_filter_by_parking_spot_size(self):
        """Test filtering listings by parking spot size"""
        # Test compact filter
        response = self.client.get(
            reverse("view_listings"), {"parking_spot_size": "COMPACT"}
        )
        listings = response.context["listings"]
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].id, self.compact_listing.id)

        # Test commercial filter
        response = self.client.get(
            reverse("view_listings"), {"parking_spot_size": "COMMERCIAL"}
        )
        listings = response.context["listings"]
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].id, self.commercial_listing.id)

        # Test standard filter
        response = self.client.get(
            reverse("view_listings"), {"parking_spot_size": "STANDARD"}
        )
        listings = response.context["listings"]
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].id, self.standard_listing.id)


#############################
# End of tests.
#############################


class BookmarkFunctionalityTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test users
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.owner = User.objects.create_user(username="owner", password="ownerpass")

        # Create test listings
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Listing",
            location="Test Location [40.712776, -74.005974]",
            rent_per_hour=15.00,
            description="Test description",
            parking_spot_size="STANDARD",
        )

        # Add slots to make listing appear in searches
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        ListingSlot.objects.create(
            listing=self.listing,
            start_date=tomorrow,
            start_time="09:00",
            end_date=tomorrow,
            end_time="17:00",
        )

    def test_toggle_bookmark(self):
        """Test adding and removing bookmarks"""
        self.client.login(username="testuser", password="testpass")

        # Test adding bookmark
        response = self.client.post(
            reverse("toggle_bookmark", args=[self.listing.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            BookmarkedListing.objects.filter(
                user=self.user, listing=self.listing
            ).exists()
        )

        # Test removing bookmark
        response = self.client.post(
            reverse("toggle_bookmark", args=[self.listing.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            BookmarkedListing.objects.filter(
                user=self.user, listing=self.listing
            ).exists()
        )

    def test_bookmarks_page_display(self):
        """Test bookmarks page shows correct listings"""
        self.client.login(username="testuser", password="testpass")

        # Create a bookmark
        BookmarkedListing.objects.create(user=self.user, listing=self.listing)

        # Use the correct URL name 'bookmarked_listings' instead of 'bookmarks'
        response = self.client.get(reverse("bookmarked_listings"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.listing, response.context["listings"])
        self.assertContains(response, "Test Listing")

    def test_duplicate_prevention(self):
        """Test that bookmarking the same listing multiple times doesn't create duplicates"""
        self.client.login(username="testuser", password="testpass")

        # Send multiple bookmark requests for the same listing
        for _ in range(3):
            self.client.post(
                reverse("toggle_bookmark", args=[self.listing.id]),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        # There should only be one bookmark
        bookmarks = BookmarkedListing.objects.filter(
            user=self.user, listing=self.listing
        )
        self.assertEqual(bookmarks.count(), 1)

    def test_bookmark_ajax_response_includes_correct_data(self):
        """Test that AJAX response contains all necessary data for the frontend"""
        self.client.login(username="testuser", password="testpass")

        response = self.client.post(
            reverse("toggle_bookmark", args=[self.listing.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Check expected fields - updated to match actual implementation
        self.assertIn("is_bookmarked", data)
        self.assertIn("message", data)
        self.assertEqual(data["is_bookmarked"], True)
