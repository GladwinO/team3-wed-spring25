from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Listing
from ..forms import ListingForm
from datetime import datetime, time, timedelta
from unittest.mock import patch


class ListingsViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user.profile.is_verified = True  # Ensure the user is verified
        self.user.profile.save()
        self.client.login(username="testuser", password="12345")
        tomorrow = datetime.now().date() + timedelta(days=1)
        self.listing = Listing.objects.create(
            user=self.user,
            title="Test Listing",
            location="Test Location [123, 456]",
            rent_per_hour=10.0,
            available_from=tomorrow,
            available_until=tomorrow,
            available_time_from=time(9, 0),  # 9:00 AM
            available_time_until=time(17, 0),  # 5:00 PM
            description="Test Description",
        )

    def test_create_listing_view_get(self):
        response = self.client.get(reverse("create_listing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/create_listing.html")
        self.assertIsInstance(response.context["form"], ListingForm)

    def test_create_listing_view_post(self):
        tomorrow = datetime.now().date() + timedelta(days=1)
        response = self.client.post(
            reverse("create_listing"),
            {
                "title": "New Listing",
                "description": "New Description",
                "rent_per_hour": 15.0,
                "available_from": tomorrow,
                "available_until": tomorrow,
                "available_time_from": "09:00",  # 9:00 AM
                "available_time_until": "17:00",  # 5:00 PM
                "location": "New Location [123, 456]",
            },
        )
        if response.status_code != 302:
            print(
                response.context["form"].errors
            )  # Print form errors if the status code is not 302
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("view_listings"))
        self.assertTrue(Listing.objects.filter(title="New Listing").exists())

    def test_view_listings_view(self):
        response = self.client.get(reverse("view_listings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/view_listings.html")

    def test_manage_listings_view(self):
        self.client.login(username="testuser", password="12345")
        response = self.client.get(reverse("manage_listings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/manage_listings.html")

    def test_edit_listing_view_get(self):
        self.client.login(username="testuser", password="12345")
        response = self.client.get(reverse("edit_listing", args=[self.listing.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/edit_listing.html")

    def test_edit_listing_view_post(self):
        self.client.login(username="testuser", password="12345")
        tomorrow = datetime.now().date() + timedelta(days=1)
        response = self.client.post(
            reverse("edit_listing", args=[self.listing.id]),
            {
                "title": "Updated Listing",
                "description": "Updated Description",
                "rent_per_hour": 20.0,
                "available_from": tomorrow,
                "available_until": tomorrow,
                "available_time_from": "09:00",  # 9:00 AM
                "available_time_until": "17:00",  # 5:00 PM
                "location": "Updated Location [123, 456]",
            },
        )
        if response.status_code != 302:
            print(
                response.context["form"].errors
            )  # Print form errors if the status code is not 302
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("manage_listings"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Updated Listing")

    def test_delete_listing_view_get(self):
        self.client.login(username="testuser", password="12345")
        response = self.client.get(reverse("delete_listing", args=[self.listing.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/confirm_delete.html")

    def test_delete_listing_view_post(self):
        self.client.login(username="testuser", password="12345")
        response = self.client.post(reverse("delete_listing", args=[self.listing.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("manage_listings"))

    def test_listing_reviews_view(self):
        response = self.client.get(reverse("listing_reviews", args=[self.listing.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/listing_reviews.html")


class ListingsFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")

        # Set a fixed "now" time for testing
        self.test_now = datetime(2025, 3, 15, 14, 30)  # March 15, 2025, 2:30 PM
        self.test_date = self.test_now.date()
        self.test_time = self.test_now.time()

    @patch("listings.views.datetime")
    def test_listing_time_filtering(self, mock_datetime):
        # Mock datetime.now() to return our fixed test time
        mock_datetime.now.return_value = self.test_now

        # Create test listings with various date/time combinations

        # 1. Future date - should be included
        _ = Listing.objects.create(
            user=self.user,
            title="Future Listing",
            location="Future Location",
            rent_per_hour=10.0,
            description="This should be included",
            available_from=self.test_date,
            available_until=self.test_date + timedelta(days=5),  # 5 days in future
            available_time_from=time(9, 0),
            available_time_until=time(17, 0),
        )

        # 2. Today with future time - should be included
        _ = Listing.objects.create(
            user=self.user,
            title="Today Future Time",
            location="Today Location",
            rent_per_hour=10.0,
            description="This should be included",
            available_from=self.test_date - timedelta(days=5),
            available_until=self.test_date,  # Today
            available_time_from=time(9, 0),
            available_time_until=time(17, 0),  # 5:00 PM (after our test time)
        )

        # 3. Today with past time - should be excluded
        _ = Listing.objects.create(
            user=self.user,
            title="Today Past Time",
            location="Today Past Location",
            rent_per_hour=10.0,
            description="This should be excluded",
            available_from=self.test_date - timedelta(days=5),
            available_until=self.test_date,  # Today
            available_time_from=time(9, 0),
            available_time_until=time(12, 0),  # 12:00 PM (before our test time)
        )

        # 4. Past date - should be excluded
        _ = Listing.objects.create(
            user=self.user,
            title="Past Listing",
            location="Past Location",
            rent_per_hour=10.0,
            description="This should be excluded",
            available_from=self.test_date - timedelta(days=10),
            available_until=self.test_date - timedelta(days=1),  # Yesterday
            available_time_from=time(9, 0),
            available_time_until=time(17, 0),
        )

        # Access the view
        response = self.client.get(reverse("view_listings"))

        # Get listings from context
        context_listings = response.context["listings"]
        listing_titles = [listing.title for listing in context_listings]

        # Verify correct listings are included/excluded
        self.assertIn("Future Listing", listing_titles)
        self.assertIn("Today Future Time", listing_titles)
        self.assertNotIn("Today Past Time", listing_titles)
        self.assertNotIn("Past Listing", listing_titles)

        # Also check by count - should be exactly 2 listings
        self.assertEqual(len(context_listings), 2)


class ListingOwnerBookingTest(TestCase):
    def setUp(self):
        # Create two users: owner and non-owner
        self.owner = User.objects.create_user(username="owner", password="ownerpass123")
        self.non_owner = User.objects.create_user(
            username="renter", password="renterpass123"
        )

        # Create a listing owned by the owner
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            location="Test Location [123.456, 789.012]",
            rent_per_hour=10.0,
            description="Test Description",
            available_from=(datetime.now() - timedelta(days=1)).date(),
            available_until=(datetime.now() + timedelta(days=30)).date(),
            available_time_from=time(9, 0),
            available_time_until=time(17, 0),
        )

        # URL for viewing listings
        self.view_listings_url = reverse("view_listings")

    def test_owner_sees_badge_not_book_button(self):
        """Test that owners see 'Your listing' badge instead of 'Book Now' button"""
        # Login as the owner
        self.client.login(username="owner", password="ownerpass123")

        # Access the view_listings page
        response = self.client.get(self.view_listings_url)

        # Check response is successful
        self.assertEqual(response.status_code, 200)

        # Check that the 'Your listing' badge is present
        self.assertContains(
            response, '<span class="badge bg-secondary">Your listing</span>'
        )

        # Check that the 'Book Now' button for this listing is NOT present
        book_url = reverse("book_listing", args=[self.listing.id])
        self.assertNotContains(
            response, f'href="{book_url}" class="btn btn-success">Book Now</a>'
        )

    def test_non_owner_sees_book_button(self):
        """Test that non-owners see the 'Book Now' button"""
        # Login as the non-owner
        self.client.login(username="renter", password="renterpass123")

        # Access the view_listings page
        response = self.client.get(self.view_listings_url)

        # Check response is successful
        self.assertEqual(response.status_code, 200)

        # Check that the 'Your listing' badge is NOT present
        self.assertNotContains(
            response, '<span class="badge bg-secondary">Your listing</span>'
        )

        # Check that the 'Book Now' button for this listing is present
        book_url = reverse("book_listing", args=[self.listing.id])
        self.assertContains(
            response, f'href="{book_url}" class="btn btn-success">Book Now</a>'
        )
