from django.test import TestCase
from django.contrib.auth.models import User
from messaging.models import Message


class MessageModelTest(TestCase):
    def setUp(self):
        """Set up test users"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="password123"
        )

    def test_create_message(self):
        """Test creating a message with required fields"""
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            subject="Test Subject",
            body="Test message body content",
        )

        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.recipient, self.user2)
        self.assertEqual(message.subject, "Test Subject")
        self.assertEqual(message.body, "Test message body content")
        self.assertFalse(message.read)
        self.assertIsNotNone(message.created_at)

    def test_message_without_subject(self):
        """Test creating a message without subject (should be allowed)"""
        message = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="No subject message"
        )

        self.assertIsNone(message.subject)
        self.assertEqual(message.body, "No subject message")

    def test_string_representation(self):
        """Test the string representation of the message"""
        message = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="Test message"
        )

        expected_str = f"Message from {self.user1.username} to {self.user2.username}"
        self.assertEqual(str(message), expected_str)

    def test_message_read_default(self):
        """Test that the 'read' field defaults to False"""
        message = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="Testing read status"
        )

        self.assertFalse(message.read)

    def test_message_read_update(self):
        """Test updating the 'read' status"""
        message = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="Testing read status update"
        )

        message.read = True
        message.save()

        # Refresh from database
        message.refresh_from_db()
        self.assertTrue(message.read)

    def test_subject_max_length(self):
        """Test subject field max length"""
        # Create a subject with max length
        max_subject = "A" * 255
        message = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            subject=max_subject,
            body="Testing subject length",
        )

        self.assertEqual(len(message.subject), 255)

    def test_cascade_deletion_sender(self):
        """Test that messages are deleted when sender is deleted"""
        message = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="Testing cascade deletion"
        )

        # Get message id before deletion
        message_id = message.id

        # Delete the sender
        self.user1.delete()

        # Check message doesn't exist
        with self.assertRaises(Message.DoesNotExist):
            Message.objects.get(id=message_id)

    def test_cascade_deletion_recipient(self):
        """Test that messages are deleted when recipient is deleted"""
        message = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="Testing cascade deletion"
        )

        # Get message id before deletion
        message_id = message.id

        # Delete the recipient
        self.user2.delete()

        # Check message doesn't exist
        with self.assertRaises(Message.DoesNotExist):
            Message.objects.get(id=message_id)

    def test_ordering_by_created_at(self):
        """Test retrieving messages in chronological order"""
        # Create multiple messages
        message1 = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="First message"
        )

        message2 = Message.objects.create(
            sender=self.user1, recipient=self.user2, body="Second message"
        )

        # Get messages in descending order of creation time
        messages = Message.objects.all().order_by("-created_at")

        # The second message should come first
        self.assertEqual(messages[0], message2)
        self.assertEqual(messages[1], message1)
