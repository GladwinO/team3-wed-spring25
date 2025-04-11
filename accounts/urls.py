from django.urls import path
from .views import (
    register,
    user_login,
    user_logout,
    verify,
    profile_view,
    change_password,
    password_change_done,
    change_email,
)

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("verify/", verify, name="verify"),
    path("profile/", profile_view, name="profile"),
    # Password change URLs
    path("password_change/", change_password, name="password_change"),
    path("password_change_done/", password_change_done, name="password_change_done"),
    path("email_change/", change_email, name="email_change"),
]
