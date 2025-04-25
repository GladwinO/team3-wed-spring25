from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Report(models.Model):
    REPORT_TYPES = (
        ("INAPPROPRIATE", "Inappropriate Content"),
        ("SPAM", "Spam"),
        ("MISLEADING", "Misleading Information"),
        ("FRAUD", "Fraudulent Activity"),
        ("OTHER", "Other"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending Review"),
        ("REVIEWING", "Under Review"),
        ("RESOLVED", "Resolved"),
        ("DISMISSED", "Dismissed"),
    )

    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reports_filed"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    reported_object = GenericForeignKey("content_type", "object_id")

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    admin_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_reports",
    )

    def __str__(self):
        return f"Report #{self.id} - {self.get_report_type_display()} - {self.status}"
