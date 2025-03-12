from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class AccountViewsTestCase(TestCase):
    def test_home_view(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")

    def test_register_view_get(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_register_view_post(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "testuser",
                "password1": "testpassword123",
                "password2": "testpassword123",
            },
        )
        self.assertEqual(
            response.status_code, 302
        )  # Redirect after successful registration
        self.assertRedirects(response, reverse("home"))

    def test_login_view_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_view_post(self):
        User.objects.create_user(username="testuser", password="testpassword123")
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "testpassword123"}
        )
        self.assertEqual(response.status_code, 302)  # Redirect after successful login
        self.assertRedirects(response, reverse("home"))

    def test_logout_view(self):
        User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)  # Redirect after logout
        self.assertRedirects(response, reverse("login"))

    def test_verify_view_get(self):
        User.objects.create_user(username="testuser", password="testpassword123")
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(reverse("verify"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/verify.html")

    def test_verify_view_post_success(self):
        user = User.objects.create_user(username="testuser", password="testpassword123")
        user.profile.is_verified = False
        user.profile.save()
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.post(reverse("verify"), {"answer": "ParkEasy"})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.profile.is_verified)

    def test_verify_view_post_failure(self):
        user = User.objects.create_user(username="testuser", password="testpassword123")
        user.profile.is_verified = False
        user.profile.save()
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.post(reverse("verify"), {"answer": "WrongAnswer"})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.profile.is_verified)
