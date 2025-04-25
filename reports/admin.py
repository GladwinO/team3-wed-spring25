from django.contrib import admin
from .models import Report


class ReportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "report_type",
        "reporter",
        "content_type",
        "status",
        "created_at",
    ]
    list_filter = ["report_type", "status", "content_type"]
    search_fields = ["description", "admin_notes", "reporter__username"]
    readonly_fields = [
        "reporter",
        "content_type",
        "object_id",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
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

    def save_model(self, request, obj, form, change):
        if obj.status in ["RESOLVED", "DISMISSED"] and not obj.resolved_by:
            obj.resolved_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Report, ReportAdmin)
