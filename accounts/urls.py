from django.urls import path
from .views import register, user_login, user_logout, verify, profile_view

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("verify/", verify, name="verify"),
    path("profile/", profile_view, name="profile"),
]
