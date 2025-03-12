from django.urls import path
from . import views

urlpatterns = [
    path("inbox/", views.inbox, name="inbox"),
    path("sent/", views.sent_messages, name="sent_messages"),
    path("compose/", views.compose_message, name="compose_message"),
    path("<int:message_id>/", views.message_detail, name="message_detail"),
    path("<int:message_id>/delete/", views.delete_message, name="delete_message"),
]
