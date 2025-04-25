# accounts/tests/test_forms.py

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.forms import EmailChangeForm, VerificationForm, AdminNotificationForm
from django.contrib.auth.models import User


class EmailChangeFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

    def test_form_valid_with_new_email(self):
        """
        Test that the form is valid with a new email address.
        """
        form = EmailChangeForm(data={"email": "new@example.com"}, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_invalid_with_same_email(self):
        """
        Test that the form is invalid when the email is the same as the current one.
        """
        form = EmailChangeForm(data={"email": "test@example.com"}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("This is already your current email", str(form.errors["email"]))

    def test_form_invalid_with_invalid_email(self):
        """
        Test that the form is invalid with an invalid email format.
        """
        form = EmailChangeForm(data={"email": "not-an-email"}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("Enter a valid email address", str(form.errors["email"]))

    def test_form_without_user(self):
        """
        Test that the form works when no user is provided.
        """
        form = EmailChangeForm(data={"email": "valid@example.com"})
        self.assertTrue(form.is_valid())


class VerificationFormTest(TestCase):
    def test_form_valid_with_required_fields(self):
        """
        Test that the form is valid with all required fields.
        """
        form_data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
        }
        # Add the required file
        file_data = {
            "verification_file": SimpleUploadedFile(
                "document.pdf", b"PDF content", content_type="application/pdf"
            ),
        }
        form = VerificationForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid())

    def test_form_valid_with_all_fields(self):
        """
        Test that the form is valid with all fields including the optional file.
        """
        form_data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
        }
        file_data = {
            "verification_file": SimpleUploadedFile(
                "document.pdf", b"PDF content", content_type="application/pdf"
            ),
        }
        form = VerificationForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_with_missing_required_fields(self):
        """
        Test that the form is invalid when required fields are missing.
        """
        form_data = {}  # No data
        form = VerificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("age", form.errors)
        self.assertIn("address", form.errors)
        self.assertIn("phone_number", form.errors)

    def test_form_invalid_with_age_below_minimum(self):
        """
        Test that the form is invalid when age is below the minimum (18).
        """
        form_data = {
            "age": 17,  # Below 18
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
        }
        form = VerificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("age", form.errors)
        self.assertIn(
            "Ensure this value is greater than or equal to 18", str(form.errors["age"])
        )

    def test_form_invalid_with_age_above_maximum(self):
        """
        Test that the form is invalid when age is above the maximum (120).
        """
        form_data = {
            "age": 121,  # Above 120
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
        }
        form = VerificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("age", form.errors)
        self.assertIn(
            "Ensure this value is less than or equal to 120", str(form.errors["age"])
        )

    def test_form_invalid_with_invalid_phone_number(self):
        """
        Test that the form is invalid with an invalid phone number format.
        """
        form_data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "not-a-phone-number",  # Invalid format
        }
        form = VerificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)
        self.assertIn(
            "Phone number must be entered in the format",
            str(form.errors["phone_number"]),
        )

    def test_form_invalid_with_non_pdf_file(self):
        """
        Test that the form is invalid when a non-PDF file is uploaded.
        """
        form_data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
        }
        file_data = {
            "verification_file": SimpleUploadedFile(
                "document.txt", b"Text content", content_type="text/plain"
            ),
        }
        form = VerificationForm(data=form_data, files=file_data)
        self.assertFalse(form.is_valid())
        self.assertIn("verification_file", form.errors)
        self.assertIn(
            "Only PDF files are allowed", str(form.errors["verification_file"])
        )


class AdminNotificationFormTest(TestCase):
    def setUp(self):
        """
        Set up test users for the form tests.
        """
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

    def test_form_valid_all_users(self):
        """
        Test that the form is valid when sending to all users.
        """
        form_data = {
            "recipient_type": "ALL",
            "subject": "Test Notification",
            "content": "This is a test notification for all users.",
        }
        form = AdminNotificationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_valid_verified_users(self):
        """
        Test that the form is valid when sending to verified users only.
        """
        form_data = {
            "recipient_type": "OWNERS",
            "subject": "Test Notification",
            "content": "This is a test notification for verified users.",
        }
        form = AdminNotificationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_valid_selected_users(self):
        """
        Test that the form is valid when sending to selected users with users provided.
        """
        form_data = {
            "recipient_type": "SELECTED",
            "subject": "Test Notification",
            "content": "This is a test notification for selected users.",
            "selected_users": [self.user1.id, self.user2.id],
        }
        form = AdminNotificationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_selected_users_without_selection(self):
        """
        Test that the form is invalid when sending to selected users without specifying any users.
        """
        form_data = {
            "recipient_type": "SELECTED",
            "subject": "Test Notification",
            "content": "This is a test notification for selected users.",
            "selected_users": [],
        }
        form = AdminNotificationForm(data=form_data)
        self.assertFalse(form.is_valid())

        # Check if the error message is in the form errors directly
        self.assertIn(
            "You must select at least one user when choosing 'Selected Users'.",
            form.errors.get("__all__", [])[0] if form.errors.get("__all__") else "",
        )

    def test_form_invalid_without_subject(self):
        """
        Test that the form is invalid when the subject is not provided.
        """
        form_data = {
            "recipient_type": "ALL",
            "subject": "",
            "content": "This is a test notification without a subject.",
        }
        form = AdminNotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("subject", form.errors)

    def test_form_invalid_without_content(self):
        """
        Test that the form is invalid when the content is not provided.
        """
        form_data = {
            "recipient_type": "ALL",
            "subject": "Test Notification",
            "content": "",
        }
        form = AdminNotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_queryset_excludes_admin_users(self):
        """
        Test that the form's queryset excludes admin users.
        """
        form = AdminNotificationForm()
        queryset = form.fields["selected_users"].queryset

        # The admin user should not be in the queryset
        self.assertNotIn(self.admin, queryset)

        # The regular users should be in the queryset
        self.assertIn(self.user1, queryset)
        self.assertIn(self.user2, queryset)
