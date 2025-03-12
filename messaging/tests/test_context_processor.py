from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from messaging.models import Message
from messaging.context_processors import unread_messages_count


class UnreadMessagesCountTest(TestCase):
    def setUp(self):
        """Set up test data and request factory"""
        self.factory = RequestFactory()

        # Create users
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="password123"
        )

        # Create some read and unread messages
        # Unread messages for user1
        for i in range(3):
            Message.objects.create(
                sender=self.user2,
                recipient=self.user1,
                subject=f"Unread message {i+1}",
                body=f"This is unread message {i+1}",
                read=False,
            )

        # Read messages for user1
        for i in range(2):
            Message.objects.create(
                sender=self.user2,
                recipient=self.user1,
                subject=f"Read message {i+1}",
                body=f"This is read message {i+1}",
                read=True,
            )

        # Unread messages for user2
        Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            subject="Unread message for user2",
            body="This is an unread message for user2",
            read=False,
        )

    def test_unread_messages_count_authenticated(self):
        """Test the context processor with an authenticated user"""
        # Create a request with user1
        request = self.factory.get("/")
        request.user = self.user1

        # Call the context processor
        context = unread_messages_count(request)

        # Check the result
        self.assertIn("unread_count", context)
        self.assertEqual(context["unread_count"], 3)

    def test_unread_messages_count_different_user(self):
        """Test the context processor with a different authenticated user"""
        # Create a request with user2
        request = self.factory.get("/")
        request.user = self.user2

        # Call the context processor
        context = unread_messages_count(request)

        # Check the result
        self.assertIn("unread_count", context)
        self.assertEqual(context["unread_count"], 1)

    def test_unread_messages_count_no_messages(self):
        """Test the context processor for a user with no messages"""
        # Create a new user without messages
        new_user = User.objects.create_user(
            username="newuser", email="new@example.com", password="password123"
        )

        # Create a request with the new user
        request = self.factory.get("/")
        request.user = new_user

        # Call the context processor
        context = unread_messages_count(request)

        # Check the result
        self.assertIn("unread_count", context)
        self.assertEqual(context["unread_count"], 0)

    def test_unread_messages_count_unauthenticated(self):
        """Test the context processor with an unauthenticated user"""
        # Create a request with an anonymous user
        request = self.factory.get("/")
        request.user = AnonymousUser()

        # Call the context processor
        context = unread_messages_count(request)

        # Check the result
        self.assertIn("unread_count", context)
        self.assertEqual(context["unread_count"], 0)
