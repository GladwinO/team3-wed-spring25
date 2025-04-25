from django.urls import path
from . import views

urlpatterns = [
    path(
        "admin/view/<int:report_id>/",
        views.admin_report_detail,
        name="admin_report_detail",
    ),
    path("admin/", views.admin_reports, name="admin_reports"),
    path(
        "<str:content_type_str>/<int:object_id>/", views.report_item, name="report_item"
    ),
]
