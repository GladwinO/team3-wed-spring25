from django.test import TestCase
from django.contrib.auth.models import User
from messaging.forms import MessageForm
from messaging.models import Message


class MessageFormTest(TestCase):
    def setUp(self):
        """Set up test users for form testing"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="password123"
        )

    def test_form_fields(self):
        """Test that the form has the correct fields"""
        form = MessageForm()
        expected_fields = ["recipient", "subject", "body"]
        self.assertEqual(list(form.fields.keys()), expected_fields)

    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            "recipient": self.user2.id,
            "subject": "Test Subject",
            "body": "Test message body content",
        }
        form = MessageForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_subject(self):
        """Test that the form is valid when subject is not provided"""
        form_data = {
            "recipient": self.user2.id,
            "subject": "",
            "body": "Test message body content",
        }
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_invalid_without_recipient(self):
        """Test that the form is invalid when recipient is not provided"""
        form_data = {"subject": "Test Subject", "body": "Test message body content"}
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("recipient", form.errors)

    def test_form_invalid_without_body(self):
        """Test that the form is invalid when body is not provided"""
        form_data = {"recipient": self.user2.id, "subject": "Test Subject", "body": ""}
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_form_invalid_recipient_not_exists(self):
        """Test that the form is invalid when the recipient doesn't exist"""
        non_existent_id = User.objects.order_by("-id").first().id + 1
        form_data = {
            "recipient": non_existent_id,
            "subject": "Test Subject",
            "body": "Test message body content",
        }
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("recipient", form.errors)

    def test_form_save(self):
        """Test saving the form creates the correct model instance"""
        form_data = {
            "recipient": self.user2.id,
            "subject": "Test Subject",
            "body": "Test message body content",
        }
        form = MessageForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Save the form but don't commit yet
        message = form.save(commit=False)
        message.sender = self.user1
        message.save()

        # Verify message was created correctly
        saved_message = Message.objects.get(subject="Test Subject")
        self.assertEqual(saved_message.sender, self.user1)
        self.assertEqual(saved_message.recipient, self.user2)
        self.assertEqual(saved_message.body, "Test message body content")

    def test_form_widget_attributes(self):
        """Test that the form widgets have the expected attributes"""
        form = MessageForm()

        # Check recipient field widget
        self.assertEqual(form.fields["recipient"].widget.__class__.__name__, "Select")
        self.assertEqual(form.fields["recipient"].widget.attrs["class"], "form-select")

        # Check subject field widget
        self.assertEqual(form.fields["subject"].widget.__class__.__name__, "TextInput")
        self.assertEqual(form.fields["subject"].widget.attrs["class"], "form-control")

        # Check body field widget
        self.assertEqual(form.fields["body"].widget.__class__.__name__, "Textarea")
        self.assertEqual(form.fields["body"].widget.attrs["class"], "form-control")
        self.assertEqual(form.fields["body"].widget.attrs["rows"], 4)
