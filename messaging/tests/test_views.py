from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from messaging.models import Message
from messaging.forms import MessageForm


class MessagingViewsTest(TestCase):
    def setUp(self):
        """Create test users and messages"""
        self.user1 = User.objects.create_user(
            username="testuser1", email="user1@test.com", password="testpassword1"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="user2@test.com", password="testpassword2"
        )
        self.user3 = User.objects.create_user(
            username="testuser3", email="user3@test.com", password="testpassword3"
        )

        self.message1 = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            subject="Test Subject 1",
            body="Test body 1",
        )

        self.message2 = Message.objects.create(
            sender=self.user2,
            recipient=self.user1,
            subject="Test Subject 2",
            body="Test body 2",
        )

        self.client = Client()

    def test_inbox_view_authenticated(self):
        """Test inbox access for authenticated users"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("inbox"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/inbox.html")
        self.assertIn("messages_inbox", response.context)
        self.assertEqual(len(response.context["messages_inbox"]), 1)
        self.assertEqual(response.context["messages_inbox"][0], self.message2)

    def test_inbox_view_unauthenticated(self):
        """Test inbox access for unauthenticated users"""
        response = self.client.get(reverse("inbox"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_sent_messages_view_authenticated(self):
        """Test sent messages access for authenticated users"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("sent_messages"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/sent_messages.html")
        self.assertIn("messages_sent", response.context)
        self.assertEqual(len(response.context["messages_sent"]), 1)
        self.assertEqual(response.context["messages_sent"][0], self.message1)

    def test_sent_messages_view_unauthenticated(self):
        """Test sent messages access for unauthenticated users"""
        response = self.client.get(reverse("sent_messages"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_compose_message_get(self):
        """Test accessing the compose message page"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("compose_message"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/compose_message.html")
        self.assertIsInstance(response.context["form"], MessageForm)

    def test_compose_message_post(self):
        """Test submitting a new message"""
        self.client.login(username="testuser1", password="testpassword1")

        data = {
            "recipient": self.user2.id,
            "subject": "New Test Subject",
            "body": "New Test body",
        }
        response = self.client.post(reverse("compose_message"), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))

        self.assertTrue(
            Message.objects.filter(
                sender=self.user1, recipient=self.user2, subject="New Test Subject"
            ).exists()
        )

    def test_message_detail_as_recipient(self):
        """Test viewing message details as recipient"""
        self.client.login(username="testuser2", password="testpassword2")
        response = self.client.get(reverse("message_detail", args=[self.message1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/message_detail.html")

        # Verify message is marked as read
        self.message1.refresh_from_db()
        self.assertTrue(self.message1.read)

    def test_message_detail_as_sender(self):
        """Test viewing message details as sender"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("message_detail", args=[self.message1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/message_detail.html")

    def test_message_detail_unauthorized(self):
        """Test unauthorized access to message details"""
        self.client.login(username="testuser3", password="testpassword3")
        response = self.client.get(reverse("message_detail", args=[self.message1.id]))

        self.assertEqual(response.status_code, 403)

    def test_delete_message_as_recipient(self):
        """Test deleting a message as recipient"""
        self.client.login(username="testuser2", password="testpassword2")
        response = self.client.post(reverse("delete_message", args=[self.message1.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertFalse(Message.objects.filter(id=self.message1.id).exists())

    def test_delete_message_as_sender(self):
        """Test deleting a message as sender"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.post(reverse("delete_message", args=[self.message1.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertFalse(Message.objects.filter(id=self.message1.id).exists())

    def test_delete_message_unauthorized(self):
        """Test unauthorized attempt to delete a message"""
        self.client.login(username="testuser3", password="testpassword3")
        response = self.client.post(reverse("delete_message", args=[self.message1.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Message.objects.filter(id=self.message1.id).exists())
