from django.urls import path

# Add this to accounts/urls.py

from .views import (
    register,
    user_login,
    user_logout,
    verify,
    profile_view,
    change_password,
    password_change_done,
    change_email,
    admin_verify_user,
    admin_verification_requests,  # Add this
    user_notifications,
    admin_send_notification,
    admin_sent_notifications,
    debug_notification_counts,
    public_profile_view,
)

urlpatterns = [
    # Existing URLs...
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("verify/", verify, name="verify"),
    path("profile/<str:username>/", public_profile_view, name="public_profile"),
    path("profile/", profile_view, name="profile"),
    path("password_change/", change_password, name="password_change"),
    path("password_change_done/", password_change_done, name="password_change_done"),
    path("email_change/", change_email, name="email_change"),
    # New and updated verification URLs
    path("admin_verify/<int:user_id>/", admin_verify_user, name="admin_verify_user"),
    path(
        "admin/verification_requests/",
        admin_verification_requests,
        name="admin_verification_requests",
    ),
    # Other admin URLs
    path("notifications/", user_notifications, name="user_notifications"),
    path(
        "admin/send_notification/",
        admin_send_notification,
        name="admin_send_notification",
    ),
    path(
        "admin/sent_notifications/",
        admin_sent_notifications,
        name="admin_sent_notifications",
    ),
    path("debug_counts/", debug_notification_counts, name="debug_notification_counts"),
]
