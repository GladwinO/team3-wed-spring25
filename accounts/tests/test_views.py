# accounts/tests/test_views.py

import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.forms import VerificationForm

# Create a temporary directory for MEDIA_ROOT during tests.
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AccountsViewsTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Delete temporary media directory and its contents.
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = Client()
        # Create a user for login and verification tests
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_home_view_redirect(self):
        """
        The home view should redirect to the 'view_listings' URL.
        """
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("view_listings"))

    def test_register_view_get(self):
        """
        A GET request to the register view should render the registration form.
        """
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")
        self.assertIn("form", response.context)

    def test_register_view_post_valid(self):
        """
        A valid POST request to the register view should create a new user and redirect to home.
        """
        data = {
            "username": "newuser",
            "password1": "complexpass123",
            "password2": "complexpass123",
        }
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_view_post_invalid(self):
        """
        An invalid POST request (e.g., mismatched passwords) to the register view
        should re-render the form with errors.
        """
        data = {
            "username": "newuser",
            "password1": "complexpass123",
            "password2": "differentpass",
        }
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)

    def test_user_login_view_get(self):
        """
        A GET request to the login view should render the login form.
        """
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertIn("form", response.context)

    def test_user_login_view_post_valid(self):
        """
        A valid POST request to the login view should log the user in and redirect to home.
        """
        data = {"username": "testuser", "password": "testpass123"}
        response = self.client.post(reverse("login"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))

    def test_user_login_view_post_invalid(self):
        """
        An invalid POST request (wrong credentials) to the login view should re-render the form with errors.
        """
        data = {"username": "testuser", "password": "wrongpass"}
        response = self.client.post(reverse("login"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)

    def test_user_logout_view(self):
        """
        The logout view should log out the user and redirect to the login page.
        """
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_verify_view_get_not_verified(self):
        """
        A GET request to the verify view for a non-verified user should render the verification form.
        """
        self.client.force_login(self.user)
        self.user.profile.is_verified = False
        self.user.profile.save()
        response = self.client.get(reverse("verify"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], VerificationForm)

    def test_verify_view_get_already_verified(self):
        """
        A GET request to the verify view for an already verified user should render the success message.
        """
        self.client.force_login(self.user)
        self.user.profile.is_verified = True
        self.user.profile.save()
        response = self.client.get(reverse("verify"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("success", response.context)
        self.assertTrue(response.context["success"])

    def test_verify_view_get_verification_pending(self):
        """
        A GET request to the verify view for a user with a pending verification request should show pending status.
        """
        self.client.force_login(self.user)
        self.user.profile.is_verified = False
        self.user.profile.verification_requested = True
        self.user.profile.save()
        response = self.client.get(reverse("verify"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")

    def test_verify_view_post_valid_information(self):
        """
        A POST request to the verify view with valid user information should create a verification request.
        """
        # Log in the user with force_login (matches pattern used in other tests)
        self.client.force_login(self.user)

        # Create a test file
        test_file = SimpleUploadedFile(
            "document.pdf", b"PDF content", content_type="application/pdf"
        )

        # Include the file in your POST data
        response = self.client.post(
            reverse("verify"),
            {
                "age": 25,
                "address": "123 Test Street, New York, NY 10001",
                "phone_number": "+1234567890",
                "verification_file": test_file,
            },
            follow=True,
        )

        self.assertIn("request_sent", response.context)

        # Add additional assertions to verify the request was created
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.verification_requested)

    def test_verify_view_post_invalid_age(self):
        """
        A POST request with an invalid age (below minimum) should show form errors.
        """
        self.client.force_login(self.user)
        data = {
            "age": 15,  # Below minimum age of 18
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
        }
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors["age"])

    def test_verify_view_post_invalid_phone(self):
        """
        A POST request with an invalid phone number format should show form errors.
        """
        self.client.force_login(self.user)
        data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "invalid-format",  # Invalid format
        }
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors["phone_number"])

    def test_verify_view_post_with_valid_pdf(self):
        """
        A POST request with valid information and a PDF file should store the file.
        """
        self.client.force_login(self.user)
        pdf_file = SimpleUploadedFile(
            "document.pdf", b"PDF content", content_type="application/pdf"
        )
        data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
            "verification_file": pdf_file,
        }
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("request_sent", response.context)

        # Refresh user profile
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.verification_file)
        self.assertTrue(self.user.profile.verification_file.name.endswith(".pdf"))

    def test_verify_view_post_with_invalid_file_type(self):
        """
        A POST request with an invalid file type should show a validation error.
        """
        self.client.force_login(self.user)
        text_file = SimpleUploadedFile(
            "document.txt", b"Text content", content_type="text/plain"
        )
        data = {
            "age": 25,
            "address": "123 Test Street, New York, NY 10001",
            "phone_number": "+1234567890",
            "verification_file": text_file,
        }
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors["verification_file"])

    def test_admin_verify_user_view_not_admin(self):
        """
        A non-admin user should not be able to access the admin verification view.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin_verify_user", args=[self.user.id]))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_admin_verify_user_view_admin_get(self):
        """
        An admin should be able to see the verification details.
        """
        # Create an admin user
        admin = User.objects.create_user(
            username="admin", password="adminpass123", is_staff=True
        )
        self.client.force_login(admin)

        # Setup user to verify
        self.user.profile.age = 25
        self.user.profile.address = "123 Test St"
        self.user.profile.phone_number = "+1234567890"
        self.user.profile.verification_requested = True
        self.user.profile.save()

        response = self.client.get(reverse("admin_verify_user", args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertIn("user_to_verify", response.context)
        self.assertEqual(response.context["user_to_verify"], self.user)

    def test_admin_verify_user_view_admin_post(self):
        """
        An admin should be able to approve a verification request.
        """
        # Create an admin user
        admin = User.objects.create_user(
            username="admin", password="adminpass123", is_staff=True
        )
        self.client.force_login(admin)

        # Setup user to verify
        self.user.profile.verification_requested = True
        self.user.profile.save()

        response = self.client.post(
            reverse("admin_verify_user", args=[self.user.id]),
            {"confirm_verification": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertIn("verification_complete", response.context)

        # Check that user is now verified
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)

    def test_admin_verify_already_verified_user(self):
        """
        When trying to verify an already verified user, show appropriate message.
        """
        # Create an admin user
        admin = User.objects.create_user(
            username="admin", password="adminpass123", is_staff=True
        )
        self.client.force_login(admin)

        # Setup user as already verified
        self.user.profile.is_verified = True
        self.user.profile.save()

        response = self.client.get(reverse("admin_verify_user", args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_verify.html")
        self.assertIn("already_verified", response.context)
        self.assertTrue(response.context["already_verified"])

    def test_profile_view_requires_login(self):
        """
        The profile view should require the user to be logged in and redirect to login if not.
        """
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        login_url = reverse("login")
        self.assertIn(login_url, response.url)

    def test_profile_view_logged_in(self):
        """
        A logged-in user should see the profile view with the correct context.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertIn("user", response.context)
        self.assertIn("unread_count", response.context)

    def test_user_notifications_view(self):
        """
        Test that the notifications view shows user messages and marks them as read.
        """
        from messaging.models import Message

        self.client.force_login(self.user)

        # Create a test message
        admin = User.objects.create_user(username="admin", is_staff=True)
        msg = Message.objects.create(
            sender=admin,
            recipient=self.user,
            subject="Test Message",
            body="This is a test message",
            read=False,
        )
        print(f"Created message: {msg}")

        response = self.client.get(reverse("user_notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/notifications.html")
        self.assertIn("messages", response.context)
