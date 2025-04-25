from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from reports.models import Report

User = get_user_model()


class ReportModelTest(TestCase):
    def setUp(self):
        # Create test users
        self.reporter = User.objects.create_user(
            username="reporter", email="reporter@example.com", password="password123"
        )
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="password123"
        )

        # Use User model as reported content for testing
        self.content_type = ContentType.objects.get_for_model(User)
        self.object_id = self.admin_user.id

        # Create a basic report
        self.report = Report.objects.create(
            reporter=self.reporter,
            content_type=self.content_type,
            object_id=self.object_id,
            report_type="INAPPROPRIATE",
            description="Test report description",
        )

    def test_report_creation(self):
        self.assertEqual(self.report.reporter, self.reporter)
        self.assertEqual(self.report.content_type, self.content_type)
        self.assertEqual(self.report.object_id, self.object_id)
        self.assertEqual(self.report.report_type, "INAPPROPRIATE")
        self.assertEqual(self.report.description, "Test report description")
        self.assertEqual(self.report.status, "PENDING")  # Default status

    def test_report_string_representation(self):
        expected = f"Report #{self.report.id} - Inappropriate Content - PENDING"
        self.assertEqual(str(self.report), expected)

    def test_report_status_update(self):
        self.report.status = "RESOLVED"
        self.report.resolved_by = self.admin_user
        self.report.admin_notes = "Issue has been addressed"
        self.report.save()

        # Refresh from database
        self.report.refresh_from_db()

        self.assertEqual(self.report.status, "RESOLVED")
        self.assertEqual(self.report.resolved_by, self.admin_user)
        self.assertEqual(self.report.admin_notes, "Issue has been addressed")

    def test_report_types_choices(self):
        for choice_key, choice_value in Report.REPORT_TYPES:
            self.report.report_type = choice_key
            self.report.save()
            self.assertEqual(self.report.report_type, choice_key)

    def test_report_status_choices(self):
        for choice_key, choice_value in Report.STATUS_CHOICES:
            self.report.status = choice_key
            self.report.save()
            self.assertEqual(self.report.status, choice_key)
