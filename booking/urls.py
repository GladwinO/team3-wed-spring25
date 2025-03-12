from django.urls import path
from . import views

urlpatterns = [
    path("book/<int:listing_id>/", views.book_listing, name="book_listing"),
    path("mybookings/", views.my_bookings, name="my_bookings"),
    path("cancel/<int:booking_id>/", views.cancel_booking, name="cancel_booking"),
    path(
        "manage-booking/<int:booking_id>/<str:action>/",
        views.manage_booking,
        name="manage_booking",
    ),
    path("review/<int:booking_id>/", views.review_booking, name="review_booking"),
]
