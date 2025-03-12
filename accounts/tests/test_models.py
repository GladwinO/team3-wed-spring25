from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import Profile


class ProfileModelTestCase(TestCase):
    def test_profile_creation(self):
        user = User.objects.create_user(username="testuser", password="testpassword123")
        self.assertIsInstance(user.profile, Profile)
        self.assertEqual(user.profile.user, user)
        self.assertFalse(user.profile.is_verified)

    def test_profile_str(self):
        user = User.objects.create_user(username="testuser", password="testpassword123")
        self.assertEqual(str(user.profile), "testuser's Profile")

    def test_profile_update(self):
        user = User.objects.create_user(username="testuser", password="testpassword123")
        user.profile.is_verified = True
        user.profile.save()
        self.assertTrue(user.profile.is_verified)

    def test_profile_signal(self):
        user = User.objects.create_user(username="testuser", password="testpassword123")
        user.username = "updateduser"
        user.save()
        self.assertEqual(user.profile.user.username, "updateduser")
