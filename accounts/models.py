# accounts/models.py
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    verification_requested = models.BooleanField(default=False)
    verification_file = models.FileField(
        upload_to="verification_documents/", null=True, blank=True
    )
    # New user information fields
    age = models.PositiveIntegerField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("SYSTEM", "System Notification"),
        ("BOOKING", "Booking Notification"),
        ("ADMIN", "Admin Notification"),
        ("VERIFICATION", "Verification Notification"),
    ]

    # Sender is optional (could be system notification)
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
        null=True,
        blank=True,
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    subject = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)  # Make sure default is False
    notification_type = models.CharField(
        max_length=15, choices=NOTIFICATION_TYPES, default="SYSTEM"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.subject}"


# Update the accounts/models.py file with this new model


class VerificationRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("DECLINED", "Declined"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verification_requests"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    decline_reason = models.TextField(blank=True, null=True)

    # Verification data will be stored in the Profile model
    # This is just for managing the verification request workflow

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Verification request for {self.user.username} ({self.get_status_display()})"
