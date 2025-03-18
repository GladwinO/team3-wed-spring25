from django.db import models
from django.contrib.auth.models import User
from listings.models import Listing
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class Booking(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("DECLINED", "Declined"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    email = models.EmailField(max_length=254, default="no-email@example.com")
    total_price = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.pk} by {self.user.username} for {self.listing.title}"

    def send_confirmation_email(self):
        """Send a confirmation email for the booking."""
        subject = f"Booking Confirmation - {self.listing.title}"

        # Create HTML content
        html_message = render_to_string(
            "booking/email/booking_confirmation.html",
            {
                "booking": self,
                "user": self.user,
                "listing": self.listing,
            },
        )

        # Create plain text content
        plain_message = strip_tags(html_message)

        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.EMAIL_HOST_USER or "noreply@parkeasy.com",
            recipient_list=[self.email],
            fail_silently=False,
        )

    def save(self, *args, **kwargs):
        """Override save to send confirmation email on status changes."""
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_status = Booking.objects.get(pk=self.pk).status

        # Save the booking
        super().save(*args, **kwargs)

        # Send email for new bookings or status changes
        if is_new or (old_status and old_status != self.status):
            self.send_confirmation_email()


class BookingSlot(models.Model):
    """
    A single interval of time within a booking.
    E.g. from 3/14 13:00 to 3/14 17:00,
    or from 3/30 10:00 to 3/30 12:00, etc.
    """

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="slots")
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()

    def __str__(self):
        return (
            f"BookingSlot for Booking #{self.booking.pk}: "
            f"{self.start_date} {self.start_time} - {self.end_date} {self.end_time}"
        )
