from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("traffic-data/", views.get_traffic_data, name="traffic_data"),
]
