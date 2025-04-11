# accounts/tests/test_views.py

import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

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
        self.assertNotIn("success", response.context)

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

    def test_verify_view_post_invalid_file_type(self):
        """
        A POST request to the verify view with an uploaded file that is not a PDF should return an error.
        """
        self.client.force_login(self.user)
        data = {"answer": "ParkEasy"}
        # Create a non-PDF file (e.g., a .txt file)
        file_data = SimpleUploadedFile(
            "test.txt", b"Some text content", content_type="text/plain"
        )
        data["verification_file"] = file_data
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("error_message", response.context)
        self.assertEqual(
            response.context["error_message"], "Only PDF files are allowed."
        )

    def test_verify_view_post_wrong_answer(self):
        """
        A POST request to the verify view with an incorrect answer should return an error message.
        """
        self.client.force_login(self.user)
        data = {"answer": "WrongAnswer"}
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("error_message", response.context)
        self.assertEqual(
            response.context["error_message"],
            "Incorrect answer, verification failed. Please try again.",
        )

    def test_verify_view_post_correct_answer_without_file(self):
        """
        A POST request to the verify view with the correct answer and no file should verify the user.
        """
        self.client.force_login(self.user)
        data = {"answer": "ParkEasy"}
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("success", response.context)
        self.assertTrue(response.context["success"])
        self.assertIn("success_message", response.context)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)

    def test_verify_view_post_correct_answer_with_file(self):
        """
        A POST request to the verify view with the correct answer and a valid PDF file should verify
        the user and save the file.
        """
        self.client.force_login(self.user)
        pdf_file = SimpleUploadedFile(
            "document.pdf", b"PDF content", content_type="application/pdf"
        )
        data = {"answer": "ParkEasy", "verification_file": pdf_file}
        response = self.client.post(reverse("verify"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")
        self.assertIn("success", response.context)
        self.assertTrue(response.context["success"])
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)
        self.assertTrue(self.user.profile.verification_file)
        # Check that the saved file's name ends with .pdf
        self.assertTrue(self.user.profile.verification_file.name.endswith(".pdf"))

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
