# listings/urls.py

from django.urls import path

from . import views

urlpatterns = [
    path("create_listing/", views.create_listing, name="create_listing"),
    path("view_listings/", views.view_listings, name="view_listings"),
    path("manage_listings/", views.manage_listings, name="manage_listings"),
    path("<int:listing_id>/edit/", views.edit_listing, name="edit_listing"),
    path("<int:listing_id>/delete/", views.delete_listing, name="delete_listing"),
    path("reviews/<int:listing_id>/", views.listing_reviews, name="listing_reviews"),
]
