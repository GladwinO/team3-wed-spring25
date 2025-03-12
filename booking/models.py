from django.db import models
from django.contrib.auth.models import User
from listings.models import Listing


class Booking(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("DECLINED", "Declined"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)

    # The date the user wants to book the spot
    booking_date = models.DateField()

    # The daily time range
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Price will be calculated based on the chosen time range
    total_price = models.DecimalField(max_digits=7, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    def __str__(self):
        return f"{self.listing.title} booked by {self.user.username} on {self.booking_date}"
