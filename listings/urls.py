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
    path("user/<str:username>/listings/", views.user_listings, name="user_listings"),
    path("map-view-listings/", views.map_view_listings, name="map_view_listings"),
    path("my_listings/", views.my_listings, name="my_listings"),
    path("map_legend/", views.map_legend, name="map_legend"),
    path("bookmark/<int:listing_id>/", views.toggle_bookmark, name="toggle_bookmark"),
    path("bookmarks/", views.bookmarked_listings, name="bookmarked_listings"),
]
