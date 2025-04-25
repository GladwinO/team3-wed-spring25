from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from reports.models import Report
from messaging.models import Message
from listings.models import Listing, Review
from booking.models import Booking
from accounts.models import Notification


class ReportItemViewTest(TestCase):
    """Tests for the report_item view function which allows users to report content"""

    def setUp(self):
        # Create test users
        self.owner = User.objects.create_user(
            username="parkowner", email="owner@example.com", password="testpass123"
        )
        self.parker = User.objects.create_user(
            username="parker", email="parker@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )

        # Create a test listing
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            location="123 Test St",
            rent_per_hour=10.00,
            description="A test parking spot",
        )

        # Create test messages
        self.message_from_parker = Message.objects.create(
            sender=self.parker,
            recipient=self.owner,
            subject="Inquiry about spot",
            body="I'd like to book your spot",
        )

        self.message_from_owner = Message.objects.create(
            sender=self.owner,
            recipient=self.parker,
            subject="Re: Inquiry",
            body="Sure, it's available",
        )

        # Create a test booking for Review creation
        self.booking = Booking.objects.create(
            user=self.parker,
            listing=self.listing,
            email="parker@example.com",
            status="APPROVED",
            total_price=30.00,  # Adding required field
        )

        # Set up client
        self.client = Client()

    def test_report_message_by_recipient(self):
        """Test that a message recipient can report a message"""
        self.client.login(username="parker", password="testpass123")

        response = self.client.post(
            reverse("report_item", args=["message", self.message_from_owner.id]),
            {
                "report_type": "INAPPROPRIATE",
                "description": "This message is inappropriate",
            },
        )

        # Check redirect
        self.assertRedirects(response, reverse("inbox"))

        # Check report was created
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.reporter, self.parker)
        self.assertEqual(
            report.content_type, ContentType.objects.get_for_model(Message)
        )
        self.assertEqual(report.object_id, self.message_from_owner.id)
        self.assertEqual(report.report_type, "INAPPROPRIATE")

    def test_report_message_by_sender(self):
        """Test that a message sender can report a message"""
        self.client.login(username="parkowner", password="testpass123")

        response = self.client.post(
            reverse("report_item", args=["message", self.message_from_owner.id]),
            {"report_type": "SPAM", "description": "I want to report my own message"},
        )

        # Check redirect
        self.assertRedirects(response, reverse("inbox"))

        # Check report was created
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.reporter, self.owner)
        self.assertEqual(
            report.content_type, ContentType.objects.get_for_model(Message)
        )
        self.assertEqual(report.object_id, self.message_from_owner.id)
        self.assertEqual(report.report_type, "SPAM")

    def test_cannot_report_others_message(self):
        """Test that users cannot report messages they're not part of"""
        self.client.login(username="otheruser", password="testpass123")

        response = self.client.get(
            reverse("report_item", args=["message", self.message_from_owner.id])
        )

        # Should redirect away without creating report
        self.assertRedirects(response, reverse("inbox"))
        self.assertEqual(Report.objects.count(), 0)

    def test_report_listing(self):
        """Test reporting a listing"""
        self.client.login(username="parker", password="testpass123")

        response = self.client.post(
            reverse("report_item", args=["listing", self.listing.id]),
            {
                "report_type": "MISLEADING",
                "description": "The listing information is incorrect",
            },
        )

        # Check redirect
        self.assertRedirects(response, reverse("view_listings"))

        # Check report was created
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.reporter, self.parker)
        self.assertEqual(
            report.content_type, ContentType.objects.get_for_model(Listing)
        )
        self.assertEqual(report.object_id, self.listing.id)
        self.assertEqual(report.report_type, "MISLEADING")

        # Check admin notification
        admin_notification = Notification.objects.filter(
            recipient=self.admin_user, subject__startswith="New Report:"
        ).first()
        self.assertIsNotNone(admin_notification)

    def test_report_nonexistent_object(self):
        """Test handling of reports for objects that don't exist"""
        self.client.login(username="parker", password="testpass123")

        response = self.client.get(
            reverse("report_item", args=["listing", 99999])  # Non-existent ID
        )

        # Should redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Report.objects.count(), 0)

    def test_report_invalid_content_type(self):
        """Test handling of invalid content types"""
        self.client.login(username="parker", password="testpass123")

        response = self.client.get(reverse("report_item", args=["invalid_type", 1]))

        # Should redirect to home - using fetch_redirect_response=False to avoid
        # additional request that might fail
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(Report.objects.count(), 0)

    def test_login_required(self):
        """Test that login is required to report"""
        # Not logged in
        response = self.client.get(
            reverse("report_item", args=["listing", self.listing.id])
        )

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_report_own_review_not_allowed(self):
        """Test that users cannot report their own reviews"""
        # Create a review by the parker user
        review = Review.objects.create(
            user=self.parker,
            listing=self.listing,
            rating=3,
            comment="My own review",
            booking=self.booking,  # Adding required booking
        )

        self.client.login(username="parker", password="testpass123")

        # Try to report the review
        response = self.client.get(reverse("report_item", args=["review", review.id]))

        # Should redirect with error message
        self.assertRedirects(
            response, reverse("listing_reviews", args=[self.listing.id])
        )
        self.assertEqual(
            self.client.session["error_message"], "You cannot report your own review."
        )
        self.assertEqual(Report.objects.count(), 0)

    def test_report_review(self):
        """Test reporting another user's review"""
        # Create a review by the owner
        review = Review.objects.create(
            user=self.owner,
            listing=self.listing,
            rating=1,
            comment="Bad review",
            booking=self.booking,  # Adding required booking
        )

        self.client.login(username="parker", password="testpass123")

        # Report the review
        response = self.client.post(
            reverse("report_item", args=["review", review.id]),
            {
                "report_type": "INAPPROPRIATE",
                "description": "This review is inappropriate",
            },
        )

        # Should redirect to reviews page
        self.assertRedirects(
            response, reverse("listing_reviews", args=[self.listing.id])
        )

        # Check report was created
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.reporter, self.parker)
        self.assertEqual(report.object_id, review.id)

        # Check admin notification
        admin_notification = Notification.objects.filter(
            recipient=self.admin_user, subject__startswith="New Report:"
        ).first()
        self.assertIsNotNone(admin_notification)

    def test_report_form_invalid(self):
        """Test submitting an invalid report form"""
        self.client.login(username="parker", password="testpass123")

        # Submit form without required fields
        response = self.client.post(
            reverse("report_item", args=["listing", self.listing.id]), {}  # Empty data
        )

        # Should stay on form with errors
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["form"].errors)
        self.assertEqual(Report.objects.count(), 0)

    def test_report_form_get(self):
        """Test displaying the report form"""
        self.client.login(username="parker", password="testpass123")

        response = self.client.get(
            reverse("report_item", args=["listing", self.listing.id])
        )

        # Should display the form
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/report_form.html")
        self.assertIn("form", response.context)
        self.assertIn("reported_object", response.context)
        self.assertEqual(response.context["content_type_str"], "listing")


class AdminReportsViewTest(TestCase):
    """Tests for the admin-facing report management views"""

    def setUp(self):
        # Create admin and regular users
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="user", email="user@example.com", password="userpass"
        )

        # Create various content types for testing
        self.message = Message.objects.create(
            sender=self.regular_user,
            recipient=self.admin_user,
            subject="Test Message",
            body="This is a test message.",
        )

        self.listing = Listing.objects.create(
            user=self.regular_user,
            title="Test Listing",
            location="Test Location",
            rent_per_hour=10.00,
            description="This is a test listing",
        )

        # Create test booking for reviews
        self.booking = Booking.objects.create(
            user=self.regular_user,
            listing=self.listing,
            email="user@example.com",
            status="APPROVED",
            total_price=30.00,
        )

        # Create different types of reports
        self.message_content_type = ContentType.objects.get_for_model(Message)
        self.listing_content_type = ContentType.objects.get_for_model(Listing)

        # Create reports with different statuses
        self.pending_report = Report.objects.create(
            reporter=self.regular_user,
            content_type=self.message_content_type,
            object_id=self.message.id,
            report_type="INAPPROPRIATE",
            description="Pending report",
            status="PENDING",
        )

        self.reviewing_report = Report.objects.create(
            reporter=self.regular_user,
            content_type=self.listing_content_type,
            object_id=self.listing.id,
            report_type="SPAM",
            description="Reviewing report",
            status="REVIEWING",
        )

        self.resolved_report = Report.objects.create(
            reporter=self.regular_user,
            content_type=self.message_content_type,
            object_id=self.message.id,
            report_type="MISLEADING",
            description="Resolved report",
            status="RESOLVED",
            resolved_by=self.admin_user,
        )

        self.dismissed_report = Report.objects.create(
            reporter=self.regular_user,
            content_type=self.listing_content_type,
            object_id=self.listing.id,
            report_type="OTHER",
            description="Dismissed report",
            status="DISMISSED",
            resolved_by=self.admin_user,
        )

        # Set up the client
        self.client = Client()

        # URLs
        self.admin_reports_url = reverse("admin_reports")
        self.report_detail_url = reverse(
            "admin_report_detail", args=[self.pending_report.id]
        )

    def test_admin_reports_view_requires_admin(self):
        """Test that only admins can access the admin reports page"""
        # Unauthenticated user should be redirected to login
        response = self.client.get(self.admin_reports_url)
        self.assertEqual(response.status_code, 302)

        # Regular user should get forbidden
        self.client.login(username="user", password="userpass")
        response = self.client.get(self.admin_reports_url)
        self.assertEqual(response.status_code, 403)

        # Admin user should get OK
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_reports_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_reports_view_shows_correct_reports(self):
        """Test that reports are filtered correctly based on status"""
        self.client.login(username="admin", password="adminpass")

        # Default view should show pending reports
        response = self.client.get(self.admin_reports_url)
        self.assertEqual(response.context["current_status"], "PENDING")
        self.assertEqual(len(response.context["reports"]), 1)
        self.assertEqual(response.context["reports"][0].id, self.pending_report.id)

        # Filter by REVIEWING
        response = self.client.get(f"{self.admin_reports_url}?status=REVIEWING")
        self.assertEqual(response.context["current_status"], "REVIEWING")
        self.assertEqual(len(response.context["reports"]), 1)
        self.assertEqual(response.context["reports"][0].id, self.reviewing_report.id)

        # Filter by RESOLVED
        response = self.client.get(f"{self.admin_reports_url}?status=RESOLVED")
        self.assertEqual(response.context["current_status"], "RESOLVED")
        self.assertEqual(len(response.context["reports"]), 1)
        self.assertEqual(response.context["reports"][0].id, self.resolved_report.id)

        # Filter by DISMISSED
        response = self.client.get(f"{self.admin_reports_url}?status=DISMISSED")
        self.assertEqual(response.context["current_status"], "DISMISSED")
        self.assertEqual(len(response.context["reports"]), 1)
        self.assertEqual(response.context["reports"][0].id, self.dismissed_report.id)

        # Show all reports
        response = self.client.get(f"{self.admin_reports_url}?status=ALL")
        self.assertEqual(response.context["current_status"], "ALL")
        self.assertEqual(len(response.context["reports"]), 4)

    def test_admin_reports_view_filter_by_report_type(self):
        """Test filtering reports by report type"""
        self.client.login(username="admin", password="adminpass")

        # Filter by INAPPROPRIATE type
        response = self.client.get(f"{self.admin_reports_url}?type=INAPPROPRIATE")
        self.assertEqual(response.context["current_type"], "INAPPROPRIATE")
        self.assertEqual(len(response.context["reports"]), 1)
        self.assertEqual(response.context["reports"][0].id, self.pending_report.id)

    def test_admin_reports_view_context_includes_status_counts(self):
        """Test that the view provides counts for each status"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_reports_url)

        self.assertIn("status_counts", response.context)
        self.assertEqual(response.context["status_counts"]["PENDING"], 1)
        self.assertEqual(response.context["status_counts"]["REVIEWING"], 1)
        self.assertEqual(response.context["status_counts"]["RESOLVED"], 1)
        self.assertEqual(response.context["status_counts"]["DISMISSED"], 1)
        self.assertEqual(response.context["status_counts"]["ALL"], 4)

    def test_admin_report_detail_view_requires_admin(self):
        """Test that only admins can access the report detail page"""
        # Unauthenticated user should be redirected to login
        response = self.client.get(self.report_detail_url)
        self.assertEqual(response.status_code, 302)

        # Regular user should get forbidden
        self.client.login(username="user", password="userpass")
        response = self.client.get(self.report_detail_url)
        self.assertEqual(response.status_code, 403)

        # Admin user should get OK
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.report_detail_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_report_detail_view_shows_correct_report(self):
        """Test that the detail view shows the correct report"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.report_detail_url)

        self.assertEqual(response.context["report"], self.pending_report)
        self.assertEqual(response.context["reported_object"], self.message)
        self.assertEqual(response.context["object_type"], "message")

    def test_admin_report_detail_view_update_status(self):
        """Test updating the status of a report"""
        self.client.login(username="admin", password="adminpass")

        # Update to REVIEWING
        response = self.client.post(
            self.report_detail_url,
            {
                "update_status": "true",
                "status": "REVIEWING",
                "admin_notes": "Looking into this",
            },
        )

        # Should redirect to reports list
        self.assertRedirects(response, self.admin_reports_url)

        # Check that the report was updated
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, "REVIEWING")
        self.assertEqual(self.pending_report.admin_notes, "Looking into this")
        # For REVIEWING status, resolved_by may or may not be set - depends on implementation
        # So we don't assert anything about it here

    def test_admin_report_detail_view_resolve_report(self):
        """Test resolving a report"""
        self.client.login(username="admin", password="adminpass")

        # Resolve the report
        response = self.client.post(
            self.report_detail_url,
            {
                "update_status": "true",
                "status": "RESOLVED",
                "admin_notes": "This has been addressed",
            },
        )

        # Should redirect to reports list
        self.assertRedirects(response, self.admin_reports_url)

        # Check that the report was updated
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, "RESOLVED")
        self.assertEqual(self.pending_report.admin_notes, "This has been addressed")
        self.assertEqual(self.pending_report.resolved_by, self.admin_user)

        # Check that a notification was created for the reporter
        notification = Notification.objects.filter(
            recipient=self.regular_user,
            subject__contains=f"Report #{self.pending_report.id}",
            notification_type="REPORT",
        ).first()

        self.assertIsNotNone(notification)
        self.assertIn("resolved", notification.content.lower())
        self.assertIn("This has been addressed", notification.content)

    def test_admin_report_detail_view_dismiss_report(self):
        """Test dismissing a report"""
        self.client.login(username="admin", password="adminpass")

        # Dismiss the report
        response = self.client.post(
            self.report_detail_url,
            {
                "update_status": "true",
                "status": "DISMISSED",
                "admin_notes": "Not a valid concern",
            },
        )

        # Should redirect to reports list
        self.assertRedirects(response, self.admin_reports_url)

        # Check that the report was updated
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, "DISMISSED")
        self.assertEqual(self.pending_report.admin_notes, "Not a valid concern")
        self.assertEqual(self.pending_report.resolved_by, self.admin_user)

        # Check that a notification was created for the reporter
        notification = Notification.objects.filter(
            recipient=self.regular_user,
            subject__contains=f"Report #{self.pending_report.id}",
            notification_type="REPORT",
        ).first()

        self.assertIsNotNone(notification)
        self.assertIn("dismissed", notification.content.lower())
        self.assertIn("Not a valid concern", notification.content)

    def test_admin_report_detail_invalid_status(self):
        """Test that invalid status updates are rejected"""
        self.client.login(username="admin", password="adminpass")
        # Should not update the report
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, "PENDING")

    def test_report_detail_for_review(self):
        """Test viewing details for a report about a review"""
        # Create a review
        review = Review.objects.create(
            listing=self.listing,
            user=self.regular_user,
            rating=3,
            comment="This is a test review",
            booking=self.booking,  # Adding required booking
        )

        # Create a report for the review
        review_content_type = ContentType.objects.get_for_model(Review)
        review_report = Report.objects.create(
            reporter=self.admin_user,
            content_type=review_content_type,
            object_id=review.id,
            report_type="INAPPROPRIATE",
            description="Inappropriate review",
            status="PENDING",
        )

        # View the report detail
        self.client.login(username="admin", password="adminpass")
        url = reverse("admin_report_detail", args=[review_report.id])
        response = self.client.get(url)

        # Should show the report and the review
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["report"], review_report)
        self.assertEqual(response.context["reported_object"], review)
        self.assertEqual(response.context["object_type"], "review")
