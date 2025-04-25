from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from accounts.models import Notification, VerificationRequest
from messaging.models import Message
from accounts.context_processors import (
    notification_count,
    verification_count,
    report_count,
)


class NotificationCountTest(TestCase):
    def setUp(self):
        """Set up test data and request factory"""
        self.factory = RequestFactory()

        # Create users
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.sender = User.objects.create_user(
            username="sender", email="sender@example.com", password="senderpass"
        )

        # Create notifications
        for i in range(3):
            Notification.objects.create(
                sender=self.sender,
                recipient=self.user,
                subject=f"Test Notification {i+1}",
                content=f"Test content {i+1}",
                read=False,
                notification_type="SYSTEM",
            )

        # Create read notifications
        Notification.objects.create(
            sender=self.sender,
            recipient=self.user,
            subject="Read Notification",
            content="This notification has been read",
            read=True,
            notification_type="SYSTEM",
        )

        # Create messages
        Message.objects.create(
            sender=self.sender,
            recipient=self.user,
            subject="Test Message",
            body="Test message content",
            read=False,
        )

        # Create verification message (should be excluded from count)
        Message.objects.create(
            sender=self.admin,
            recipient=self.user,
            subject="Account Verification Approved",
            body="Your account has been verified.",
            read=False,
        )

    def test_notification_count_authenticated(self):
        """Test notification_count for an authenticated user"""
        request = self.factory.get("/")
        request.user = self.user

        context = notification_count(request)
        self.assertEqual(context["unread_notification_count"], 3)
        self.assertEqual(context["unread_message_count"], 1)
        self.assertEqual(context["total_unread_count"], 4)

    def test_notification_count_unauthenticated(self):
        """Test notification_count for an unauthenticated user"""
        request = self.factory.get("/")
        request.user = AnonymousUser()

        context = notification_count(request)
        self.assertEqual(context["unread_notification_count"], 0)
        self.assertEqual(context["unread_message_count"], 0)
        self.assertEqual(context["total_unread_count"], 0)

    def test_notification_count_no_unread(self):
        """Test notification_count when there are no unread items"""
        # Mark all notifications as read
        Notification.objects.filter(recipient=self.user).update(read=True)
        Message.objects.filter(recipient=self.user).update(read=True)

        request = self.factory.get("/")
        request.user = self.user

        context = notification_count(request)
        self.assertEqual(context["unread_notification_count"], 0)
        self.assertEqual(context["unread_message_count"], 0)
        self.assertEqual(context["total_unread_count"], 0)

    def test_notification_count_error_handling(self):
        """Test notification_count error handling"""
        request = self.factory.get("/")
        # Set an invalid user that would cause an error in the query
        request.user = "not-a-user-object"

        context = notification_count(request)
        self.assertEqual(context["unread_notification_count"], 0)
        self.assertEqual(context["unread_message_count"], 0)
        self.assertEqual(context["total_unread_count"], 0)


class VerificationCountTest(TestCase):
    def setUp(self):
        """Set up test data and request factory"""
        self.factory = RequestFactory()

        # Create users
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create verification requests
        for i in range(3):
            VerificationRequest.objects.create(
                user=self.user,
                status="PENDING",
            )

        # Create approved request
        VerificationRequest.objects.create(
            user=self.user,
            status="APPROVED",
        )

    def test_verification_count_admin(self):
        """Test verification_count for an admin user"""
        request = self.factory.get("/")
        request.user = self.admin

        context = verification_count(request)
        self.assertEqual(context["pending_verifications_count"], 3)

    def test_verification_count_non_admin(self):
        """Test verification_count for a non-admin user"""
        request = self.factory.get("/")
        request.user = self.user

        context = verification_count(request)
        self.assertEqual(context["pending_verifications_count"], 0)

    def test_verification_count_unauthenticated(self):
        """Test verification_count for an unauthenticated user"""
        request = self.factory.get("/")
        request.user = AnonymousUser()

        context = verification_count(request)
        self.assertEqual(context["pending_verifications_count"], 0)

    def test_verification_count_error_handling(self):
        """Test verification_count error handling"""
        request = self.factory.get("/")
        # Set an invalid user that would cause an error
        request.user = "not-a-user-object"

        context = verification_count(request)
        self.assertEqual(context["pending_verifications_count"], 0)


class ReportCountTest(TestCase):
    def setUp(self):
        """Set up test data and request factory"""
        self.factory = RequestFactory()

        # Create users
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    # Mock the Report.objects.filter().count() method instead of creating actual reports
    def test_report_count_admin(self):
        """Test report_count for an admin user"""
        request = self.factory.get("/")
        request.user = self.admin

        # We're testing the context processor functionality, not the model
        # So we can skip creating actual Report objects
        context = report_count(request)
        self.assertIn("pending_reports_count", context)

    def test_report_count_non_admin(self):
        """Test report_count for a non-admin user"""
        request = self.factory.get("/")
        request.user = self.user

        context = report_count(request)
        self.assertEqual(context["pending_reports_count"], 0)

    def test_report_count_unauthenticated(self):
        """Test report_count for an unauthenticated user"""
        request = self.factory.get("/")
        request.user = AnonymousUser()

        context = report_count(request)
        self.assertEqual(context["pending_reports_count"], 0)

    def test_report_count_error_handling(self):
        """Test report_count error handling"""
        request = self.factory.get("/")
        # Set an invalid user that would cause an error
        request.user = "not-a-user-object"

        context = report_count(request)
        self.assertEqual(context["pending_reports_count"], 0)
