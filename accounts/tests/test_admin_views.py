# accounts/tests/test_additional_views.py

import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Notification, VerificationRequest
from accounts.views import create_notification

# Create a temporary directory for MEDIA_ROOT during tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AdminVerificationViewsTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Delete temporary media directory and its contents
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = Client()

        # Create an admin user
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )

        # Create a regular user with a verification request
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.user.profile.verification_requested = True
        self.user.profile.save()
        self.verification_request = VerificationRequest.objects.create(
            user=self.user, status="PENDING"
        )

        # User with verification document
        self.user_with_doc = User.objects.create_user(
            username="userdoc", email="userdoc@example.com", password="testpass123"
        )
        self.user_with_doc.profile.verification_requested = True
        pdf_file = SimpleUploadedFile(
            "document.pdf", b"PDF content", content_type="application/pdf"
        )
        self.user_with_doc.profile.verification_file = pdf_file
        self.user_with_doc.profile.save()
        self.verification_request_with_doc = VerificationRequest.objects.create(
            user=self.user_with_doc, status="PENDING"
        )

        # Create a verified user
        self.verified_user = User.objects.create_user(
            username="verified", email="verified@example.com", password="testpass123"
        )
        self.verified_user.profile.is_verified = True
        self.verified_user.profile.save()

        # URLs
        self.admin_verification_requests_url = reverse("admin_verification_requests")
        self.admin_verify_user_url = reverse("admin_verify_user", args=[self.user.id])
        self.admin_verify_user_with_doc_url = reverse(
            "admin_verify_user", args=[self.user_with_doc.id]
        )
        self.admin_verify_verified_user_url = reverse(
            "admin_verify_user", args=[self.verified_user.id]
        )

    def test_admin_verification_requests_admin_access(self):
        """Test that admin can access the verification requests page"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_verification_requests_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verification_requests.html")
        self.assertIn("verification_requests", response.context)
        self.assertEqual(len(response.context["verification_requests"]), 2)

    def test_admin_verification_requests_user_forbidden(self):
        """Test that non-admin users cannot access verification requests"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.admin_verification_requests_url)
        self.assertEqual(response.status_code, 403)

    def test_admin_verify_user_get(self):
        """Test admin can see verification details"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_verify_user_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertEqual(response.context["user_to_verify"], self.user)
        self.assertFalse(response.context["has_verification_file"])

    def test_admin_verify_user_with_doc_get(self):
        """Test admin can see verification details with document"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_verify_user_with_doc_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertEqual(response.context["user_to_verify"], self.user_with_doc)
        self.assertTrue(response.context["has_verification_file"])

    def test_admin_verify_already_verified_user(self):
        """Test viewing already verified user"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_verify_verified_user_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertTrue(response.context["already_verified"])
        self.assertEqual(response.context["username"], self.verified_user.username)

    def test_admin_verify_user_approve(self):
        """Test approving a verification request"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(
            self.admin_verify_user_url, {"confirm_verification": "true"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertTrue(response.context["verification_complete"])

        # Check that the user is now verified
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)

        # Check that the verification request is updated
        self.verification_request.refresh_from_db()
        self.assertEqual(self.verification_request.status, "APPROVED")

        # Check that a notification was created
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user, subject="Account Verification Approved"
            ).exists()
        )

    def test_admin_verify_user_decline_no_reason(self):
        """Test declining a verification request without providing a reason"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(
            self.admin_verify_user_url, {"decline_verification": "true"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        # Should contain the user_to_verify since we're staying on the form
        self.assertIn("user_to_verify", response.context)

        # User should still be unverified
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_verified)

    def test_admin_verify_user_decline_with_reason(self):
        """Test declining a verification request with a reason"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(
            self.admin_verify_user_url,
            {
                "decline_verification": "true",
                "decline_reason": "Document not clear enough.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertTrue(response.context["verification_declined"])

        # Check that the verification request is updated
        self.verification_request.refresh_from_db()
        self.assertEqual(self.verification_request.status, "DECLINED")
        self.assertEqual(
            self.verification_request.decline_reason, "Document not clear enough."
        )

        # Check that a notification was created
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user, subject="Account Verification Declined"
            ).exists()
        )

    def test_admin_verify_user_non_admin_forbidden(self):
        """Test that non-admin users cannot access verification page"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.admin_verify_user_url)
        self.assertEqual(response.status_code, 403)


class NotificationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create users
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="userpass1"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="userpass2"
        )
        self.verified_user = User.objects.create_user(
            username="verified", email="verified@example.com", password="verifiedpass"
        )
        self.verified_user.profile.is_verified = True
        self.verified_user.profile.save()

        # Create notifications
        Notification.objects.create(
            sender=self.admin,
            recipient=self.user1,
            subject="Test Notification 1",
            content="Test content 1",
            read=False,
            notification_type="SYSTEM",
        )
        Notification.objects.create(
            sender=self.admin,
            recipient=self.user1,
            subject="Test Notification 2",
            content="Test content 2",
            read=True,
            notification_type="ADMIN",
        )

        # URLs
        self.user_notifications_url = reverse("user_notifications")
        self.admin_send_notification_url = reverse("admin_send_notification")
        self.admin_sent_notifications_url = reverse("admin_sent_notifications")
        self.debug_notification_counts_url = reverse("debug_notification_counts")

    def test_user_notifications_view(self):
        """Test user notifications view"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(self.user_notifications_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/notifications.html")
        self.assertIn("notifications", response.context)
        self.assertEqual(len(response.context["notifications"]), 2)

        # Check that notifications are marked as read
        self.assertFalse(
            Notification.objects.filter(recipient=self.user1, read=False).exists()
        )

    def test_admin_send_notification_get(self):
        """Test admin send notification form display"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_send_notification_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_send_notification.html")
        self.assertIn("form", response.context)

    def test_admin_send_notification_post_all_users(self):
        """Test sending notification to all users"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(
            self.admin_send_notification_url,
            {
                "recipient_type": "ALL",
                "subject": "Test Notification",
                "content": "This is a test notification for all users.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_notification_sent.html")
        self.assertEqual(
            response.context["recipient_count"], 3
        )  # should be all non-admin users

        # Check that notifications were created
        self.assertEqual(
            Notification.objects.filter(
                sender=self.admin,
                subject="Test Notification",
                notification_type="ADMIN",
            ).count(),
            3,  # One for each non-admin user
        )

    def test_admin_send_notification_post_verified_users(self):
        """Test sending notification to verified users only"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(
            self.admin_send_notification_url,
            {
                "recipient_type": "OWNERS",
                "subject": "Test Notification",
                "content": "This is a test notification for verified users.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_notification_sent.html")
        self.assertEqual(response.context["recipient_count"], 1)  # only verified_user

        # Check that notification was created
        self.assertTrue(
            Notification.objects.filter(
                sender=self.admin,
                recipient=self.verified_user,
                subject="Test Notification",
                notification_type="ADMIN",
            ).exists()
        )

    def test_admin_send_notification_post_selected_users(self):
        """Test sending notification to selected users"""
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(
            self.admin_send_notification_url,
            {
                "recipient_type": "SELECTED",
                "subject": "Test Notification",
                "content": "This is a test notification for selected users.",
                "selected_users": [self.user1.id, self.user2.id],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_notification_sent.html")
        self.assertEqual(response.context["recipient_count"], 2)

        # Check that notifications were created for both selected users
        self.assertEqual(
            Notification.objects.filter(
                sender=self.admin,
                subject="Test Notification",
                notification_type="ADMIN",
                recipient__in=[self.user1, self.user2],
            ).count(),
            2,
        )

    def test_admin_send_notification_non_admin_forbidden(self):
        """Test that non-admin users cannot access send notification page"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(self.admin_send_notification_url)
        self.assertEqual(response.status_code, 403)

    def test_admin_sent_notifications(self):
        """Test viewing sent notifications"""
        # Create some test notifications first
        create_notification(
            sender=self.admin,
            recipient=self.user1,
            subject="Admin Notification",
            content="This is an admin notification.",
            notification_type="ADMIN",
        )
        create_notification(
            sender=self.admin,
            recipient=self.user2,
            subject="Admin Notification",
            content="This is an admin notification.",
            notification_type="ADMIN",
        )

        self.client.login(username="admin", password="adminpass")
        response = self.client.get(self.admin_sent_notifications_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_sent_notifications.html")
        self.assertIn("notification_groups", response.context)

    def test_admin_sent_notifications_non_admin_forbidden(self):
        """Test that non-admin users cannot access sent notifications page"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(self.admin_sent_notifications_url)
        self.assertEqual(response.status_code, 403)

    def test_debug_notification_counts(self):
        """Test debug notification counts view"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(self.debug_notification_counts_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/debug_counts.html")
        self.assertIn("unread_notification_count", response.context)
        self.assertIn("unread_message_count", response.context)


class PublicProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="userpass1"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="userpass2"
        )

        # Create a verified user with profile
        self.verified_user = User.objects.create_user(
            username="verified", email="verified@example.com", password="verifiedpass"
        )
        self.verified_user.profile.is_verified = True
        self.verified_user.profile.save()

        # Create a user with pending verification
        self.pending_user = User.objects.create_user(
            username="pending", email="pending@example.com", password="pendingpass"
        )
        VerificationRequest.objects.create(user=self.pending_user, status="PENDING")

    def test_public_profile_view(self):
        """Test viewing another user's public profile"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(reverse("public_profile", args=["user2"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/public_profile.html")
        self.assertEqual(response.context["profile_user"], self.user2)
        self.assertFalse(response.context["is_verified"])
        self.assertFalse(response.context["pending_verification"])

    def test_public_profile_view_verified_user(self):
        """Test viewing a verified user's public profile"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(reverse("public_profile", args=["verified"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/public_profile.html")
        self.assertEqual(response.context["profile_user"], self.verified_user)
        self.assertTrue(response.context["is_verified"])

    def test_public_profile_view_pending_user(self):
        """Test viewing a pending user's public profile"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(reverse("public_profile", args=["pending"]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/public_profile.html")
        self.assertEqual(response.context["profile_user"], self.pending_user)
        self.assertFalse(response.context["is_verified"])
        self.assertTrue(response.context["pending_verification"])

    def test_public_profile_view_own_profile_redirects(self):
        """Test that viewing your own public profile redirects to profile view"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(reverse("public_profile", args=["user1"]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profile"))

    def test_public_profile_nonexistent_user(self):
        """Test viewing a nonexistent user's profile results in 404"""
        self.client.login(username="user1", password="userpass1")
        response = self.client.get(reverse("public_profile", args=["nonexistent"]))

        self.assertEqual(response.status_code, 404)
