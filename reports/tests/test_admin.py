from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from reports.admin import ReportAdmin
from reports.models import Report


class MockRequest:
    def __init__(self, user=None):
        self.user = user


class ReportAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ReportAdmin(Report, self.site)

        # Create test users
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password",
            is_staff=True,
        )
        self.reporter = User.objects.create_user(
            username="reporter", email="reporter@example.com", password="password"
        )

        # Create a report using User model as content type for simplicity
        self.content_type = ContentType.objects.get_for_model(User)
        self.report = Report.objects.create(
            reporter=self.reporter,
            content_type=self.content_type,
            object_id=self.reporter.id,
            report_type="INAPPROPRIATE",
            description="Test report description",
            status="PENDING",
        )

    def test_list_display(self):
        """Test that the list_display attribute is correctly set up"""
        self.assertEqual(
            list(self.admin.list_display),
            ["id", "report_type", "reporter", "content_type", "status", "created_at"],
        )

    def test_list_filter(self):
        """Test that the list_filter attribute is correctly set up"""
        self.assertEqual(
            list(self.admin.list_filter), ["report_type", "status", "content_type"]
        )

    def test_search_fields(self):
        """Test that the search_fields attribute is correctly set up"""
        self.assertEqual(
            list(self.admin.search_fields),
            ["description", "admin_notes", "reporter__username"],
        )

    def test_readonly_fields(self):
        """Test that the readonly_fields attribute is correctly set up"""
        self.assertEqual(
            list(self.admin.readonly_fields),
            ["reporter", "content_type", "object_id", "created_at", "updated_at"],
        )

    def test_fieldsets(self):
        """Test that the fieldsets attribute is correctly set up"""
        expected_fieldsets = (
            (
                "Report Information",
                {
                    "fields": (
                        "reporter",
                        "content_type",
                        "object_id",
                        "report_type",
                        "description",
                    )
                },
            ),
            ("Status", {"fields": ("status", "admin_notes", "resolved_by")}),
            ("Timestamps", {"fields": ("created_at", "updated_at")}),
        )
        self.assertEqual(self.admin.fieldsets, expected_fieldsets)

    def test_save_model_sets_resolved_by(self):
        """Test that save_model sets resolved_by when status changes to RESOLVED"""
        # Create a mock request with the admin user
        request = MockRequest(user=self.admin_user)

        # Update the report status to RESOLVED
        self.report.status = "RESOLVED"

        # Call save_model
        self.admin.save_model(request, self.report, None, False)

        # Check that resolved_by was set to the admin user
        self.assertEqual(self.report.resolved_by, self.admin_user)

    def test_save_model_sets_resolved_by_for_dismissed(self):
        """Test that save_model sets resolved_by when status changes to DISMISSED"""
        # Create a mock request with the admin user
        request = MockRequest(user=self.admin_user)

        # Update the report status to DISMISSED
        self.report.status = "DISMISSED"

        # Call save_model
        self.admin.save_model(request, self.report, None, False)

        # Check that resolved_by was set to the admin user
        self.assertEqual(self.report.resolved_by, self.admin_user)

    def test_save_model_doesnt_override_resolved_by(self):
        """Test that save_model doesn't override resolved_by if it's already set"""
        # Create a mock request with the admin user
        request = MockRequest(user=self.admin_user)

        # Set the resolved_by field to a different user
        other_user = User.objects.create_user(
            username="other_admin", email="other@example.com", password="password"
        )
        self.report.resolved_by = other_user
        self.report.status = "RESOLVED"

        # Call save_model
        self.admin.save_model(request, self.report, None, False)

        # Check that resolved_by was not changed
        self.assertEqual(self.report.resolved_by, other_user)

    def test_save_model_doesnt_set_resolved_by_for_other_statuses(self):
        """Test that save_model doesn't set resolved_by for PENDING or REVIEWING statuses"""
        # Create a mock request with the admin user
        request = MockRequest(user=self.admin_user)

        # Test with PENDING status
        self.report.status = "PENDING"
        self.report.resolved_by = None

        # Call save_model
        self.admin.save_model(request, self.report, None, False)

        # Check that resolved_by is still None
        self.assertIsNone(self.report.resolved_by)

        # Test with REVIEWING status
        self.report.status = "REVIEWING"

        # Call save_model
        self.admin.save_model(request, self.report, None, False)

        # Check that resolved_by is still None
        self.assertIsNone(self.report.resolved_by)
