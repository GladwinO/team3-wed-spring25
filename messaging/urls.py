from django.urls import path
from . import views

urlpatterns = [
    path("inbox/", views.inbox, name="inbox"),
    path("sent/", views.sent_messages, name="sent_messages"),
    path("compose/", views.compose_message, name="compose_message"),
    path(
        "compose/admin/",
        views.compose_message,
        {"admin_message": True},
        name="compose_admin_message",
    ),
    path("<int:message_id>/", views.message_detail, name="message_detail"),
    path(
        "compose/<int:recipient_id>/", views.compose_message, name="compose_message_to"
    ),
    path("<int:message_id>/delete/", views.delete_message, name="delete_message"),
]
