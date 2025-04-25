# accounts/tests/test_models.py

import shutil
import tempfile

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Profile

# Create a temporary directory for MEDIA_ROOT during tests.
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProfileModelTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Delete temporary media directory and all its contents.
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_profile_creation_on_user_creation(self):
        """
        Test that a Profile is automatically created when a User is created,
        and that its default values are set as expected.
        """
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertTrue(hasattr(user, "profile"))
        self.assertFalse(user.profile.is_verified)
        self.assertFalse(user.profile.verification_requested)
        # Check that the file field is falsy (None or an empty string)
        self.assertFalse(
            user.profile.verification_file, "verification_file should be empty or None"
        )
        # Check that new fields are initially None
        self.assertIsNone(user.profile.age)
        self.assertIsNone(user.profile.address)
        self.assertIsNone(user.profile.phone_number)

    def test_profile_str_method(self):
        """
        Test that the __str__ method of Profile returns the expected string.
        """
        user = User.objects.create_user(username="john", password="testpass123")
        self.assertEqual(str(user.profile), "john's Profile")

    def test_profile_update_on_user_save(self):
        """
        Test that saving the User (which triggers the post_save signal)
        saves the associated Profile.
        """
        user = User.objects.create_user(username="testuser2", password="testpass123")
        user.profile.is_verified = True
        user.profile.verification_requested = True
        user.save()
        profile = Profile.objects.get(user=user)
        self.assertTrue(profile.is_verified)
        self.assertTrue(profile.verification_requested)

    def test_profile_verification_info_update(self):
        """
        Test that the verification information fields can be updated properly.
        """
        user = User.objects.create_user(username="verifyuser", password="testpass123")
        user.profile.age = 25
        user.profile.address = "123 Test Street, New York, NY 10001"
        user.profile.phone_number = "+1234567890"
        user.profile.save()

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.age, 25)
        self.assertEqual(profile.address, "123 Test Street, New York, NY 10001")
        self.assertEqual(profile.phone_number, "+1234567890")

    def test_profile_file_field(self):
        """
        Test that the verification_file field can accept a PDF file.
        """
        user = User.objects.create_user(username="fileuser", password="testpass123")
        # Create a simple PDF file
        pdf_file = SimpleUploadedFile(
            "test.pdf", b"PDF file content", content_type="application/pdf"
        )
        user.profile.verification_file = pdf_file
        user.profile.save()
        profile = Profile.objects.get(user=user)
        self.assertTrue(profile.verification_file)
        # Check that the file name ends with .pdf
        self.assertTrue(profile.verification_file.name.endswith(".pdf"))
