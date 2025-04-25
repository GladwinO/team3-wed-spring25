from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    PasswordChangeForm,
)
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .forms import (
    EmailChangeForm,
    VerificationForm,
    AdminNotificationForm,
)  # Update import
from .models import Notification, VerificationRequest

# Import the messaging model and User to send admin notifications.
from messaging.models import Message
from django.contrib.auth.models import User


def home(request):
    return redirect("view_listings")


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log in the user after registration
            return redirect("home")  # Redirect to homepage
    else:
        form = UserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")  # Redirect to homepage
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("login")  # Redirect to login page after logout


# Add these updated functions to accounts/views.py


@login_required
def verify(request):
    """
    Handles account verification requests.
    Collects user information for verification and creates a VerificationRequest.
    Prevents users from submitting multiple verification requests.
    """
    # If already verified, show success page
    if request.user.profile.is_verified:
        return render(request, "accounts/verify.html", {"success": True})

    # If verification already requested but not approved yet, show pending status
    # Check for any pending verification requests
    pending_request = VerificationRequest.objects.filter(
        user=request.user, status="PENDING"
    ).exists()

    if pending_request:
        return render(request, "accounts/verify.html", {"pending": True})

    if request.method == "POST":
        form = VerificationForm(request.POST, request.FILES)
        if form.is_valid():
            # Update user profile with form data
            profile = request.user.profile
            profile.age = form.cleaned_data["age"]
            profile.address = form.cleaned_data["address"]
            profile.phone_number = form.cleaned_data["phone_number"]

            # Save verification file if provided
            verification_file = form.cleaned_data["verification_file"]
            if verification_file:
                profile.verification_file = verification_file

            # Save profile changes
            profile.save()

            # Create a verification request
            VerificationRequest.objects.create(user=request.user, status="PENDING")

            # Update profile to indicate verification requested
            profile.verification_requested = True
            profile.save()

            # Return a confirmation page
            context = {
                "request_sent": True,
                "success_message": "Your verification request has been sent for review.\
                    You will be notified once it is approved.",
            }
            return render(request, "accounts/verify.html", context)
    else:
        form = VerificationForm()

    return render(request, "accounts/verify.html", {"form": form})


@login_required
def admin_verification_requests(request):
    """
    View for administrators to see all pending verification requests.
    """
    # Check if the current user is an admin
    if not request.user.is_staff:
        return HttpResponseForbidden(
            "You do not have permission to view verification requests."
        )

    # Get all pending verification requests
    verification_requests = VerificationRequest.objects.filter(
        status="PENDING"
    ).order_by("-created_at")

    return render(
        request,
        "accounts/admin_verification_requests.html",
        {"verification_requests": verification_requests},
    )


@login_required
def admin_verify_user(request, user_id):
    """
    View for administrators to verify users directly.
    Now supports both approving and declining verification requests with reasons.
    """
    # Check if the current user is an admin
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to verify users.")

    # Get the user to verify
    user_to_verify = get_object_or_404(User, pk=user_id)

    # Check if user is already verified
    if user_to_verify.profile.is_verified:
        return render(
            request,
            "accounts/admin_verify.html",
            {"already_verified": True, "username": user_to_verify.username},
        )

    # Find the pending verification request
    try:
        verification_request = VerificationRequest.objects.get(
            user=user_to_verify, status="PENDING"
        )
    except VerificationRequest.DoesNotExist:
        # If no request exists, check if there are any older requests
        has_request = VerificationRequest.objects.filter(user=user_to_verify).exists()
        if not has_request:
            # Create a new request if none exists
            verification_request = VerificationRequest.objects.create(
                user=user_to_verify, status="PENDING"
            )
        else:
            # Get the most recent request
            verification_request = (
                VerificationRequest.objects.filter(user=user_to_verify)
                .order_by("-created_at")
                .first()
            )

    if request.method == "POST":
        if "confirm_verification" in request.POST:
            # Process verification approval
            user_to_verify.profile.is_verified = True
            user_to_verify.profile.save()

            # Update verification request status
            verification_request.status = "APPROVED"
            verification_request.save()

            # Create a notification for the verified user
            Notification.objects.create(
                sender=request.user,
                recipient=user_to_verify,
                subject="Account Verification Approved",
                content="Congratulations! Your account has been verified. \
                    You can now post parking spots on ParkEasy.",
                notification_type="VERIFICATION",
            )

            # Show confirmation page
            return render(
                request,
                "accounts/admin_verify.html",
                {"verification_complete": True, "username": user_to_verify.username},
            )

        elif "decline_verification" in request.POST:
            # Get the reason for declining
            decline_reason = request.POST.get("decline_reason", "")

            if not decline_reason:
                # If no reason provided, show an error
                return render(
                    request,
                    "accounts/admin_verify.html",
                    {
                        "user_to_verify": user_to_verify,
                        "has_verification_file": bool(
                            user_to_verify.profile.verification_file
                        ),
                        "error_message": "Please provide a reason for declining the verification request.",
                    },
                )

            # Update verification request status
            verification_request.status = "DECLINED"
            verification_request.decline_reason = decline_reason
            verification_request.save()

            # Create a notification for the user
            Notification.objects.create(
                sender=request.user,
                recipient=user_to_verify,
                subject="Account Verification Declined",
                content=f"Your account verification has been declined for the following reason:\
                    \n\n{decline_reason}\n\
                        \nPlease submit a new verification request with updated information or documents.",
                notification_type="VERIFICATION",
            )

            # Show confirmation page
            return render(
                request,
                "accounts/admin_verify.html",
                {"verification_declined": True, "username": user_to_verify.username},
            )

    # Show verification details and confirmation form
    return render(
        request,
        "accounts/admin_verify.html",
        {
            "user_to_verify": user_to_verify,
            "has_verification_file": bool(user_to_verify.profile.verification_file),
        },
    )


@login_required
def user_notifications(request):
    """
    Display all notifications for the user, including system messages,
    booking notifications, and admin messages.
    """
    # Get all notifications for this user
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )

    # Mark all as read (do this before rendering the template)
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)

    # Get verification messages from the Message model for backward compatibility
    verification_messages = Message.objects.filter(
        recipient=request.user, subject="Account Verification Approved"
    ).order_by("-created_at")

    # Mark verification messages as read too
    Message.objects.filter(
        recipient=request.user, subject="Account Verification Approved", read=False
    ).update(read=True)

    return render(
        request,
        "accounts/notifications.html",
        {
            "notifications": notifications,
            "verification_messages": verification_messages,
        },
    )


@login_required
def profile_view(request):
    # Get messages from session if present
    success_message = request.session.pop("success_message", None)
    error_message = request.session.pop("error_message", None)

    # Calculate unread notifications count (already available from context processor)
    # We don't need to calculate it here, but we'll keep track of verification status

    # Check verification status
    is_verified = request.user.profile.is_verified
    verification_requested = request.user.profile.verification_requested

    # Add the more specific query
    pending_verification = VerificationRequest.objects.filter(
        user=request.user, status="PENDING"
    ).exists()

    # Pass both to the template
    return render(
        request,
        "accounts/profile.html",
        {
            "user": request.user,
            "success_message": success_message,
            "error_message": error_message,
            "is_verified": is_verified,
            "verification_requested": verification_requested,
            "pending_verification": pending_verification,
        },
    )


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Prevent user from being logged out.
            update_session_auth_hash(request, user)
            return redirect("password_change_done")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/password_change.html", {"form": form})


@login_required
def password_change_done(request):
    request.session["success_message"] = "Password changed successfully!"
    return redirect("profile")


@login_required
def change_email(request):
    # Determine if the user is adding a new email.
    is_adding_email = request.user.email == "" or request.user.email is None

    if request.method == "POST":
        form = EmailChangeForm(request.POST, user=request.user)
        if form.is_valid():
            request.user.email = form.cleaned_data["email"]
            request.user.save()

            if is_adding_email:
                request.session["success_message"] = "Email added successfully!"
            else:
                request.session["success_message"] = "Email updated successfully!"

            return redirect("profile")
    else:
        form = EmailChangeForm(user=request.user)

    return render(
        request,
        "accounts/change_email.html",
        {"form": form, "is_adding_email": is_adding_email},
    )


@login_required
def admin_send_notification(request):
    """
    View for administrators to send notifications to users.
    Allows admins to send to all users, only parking spot owners (verified users), or selected users.
    All registered users can receive notifications regardless of verification status.
    """
    # Check if the current user is an admin
    if not request.user.is_staff:
        return HttpResponseForbidden(
            "You do not have permission to send notifications."
        )

    if request.method == "POST":
        form = AdminNotificationForm(request.POST)

        if form.is_valid():
            recipient_type = form.cleaned_data["recipient_type"]
            subject = form.cleaned_data["subject"]
            content = form.cleaned_data["content"]

            # Determine recipients based on the type
            if recipient_type == "ALL":
                # Send to all registered users (except other admins)
                recipients = User.objects.exclude(is_staff=True)
            elif recipient_type == "OWNERS":
                # Get verified users (potential parking spot owners)

                recipients = User.objects.filter(profile__is_verified=True).exclude(
                    is_staff=True
                )
            else:  # 'SELECTED'
                recipients = form.cleaned_data["selected_users"]

            # Create notifications for each recipient with our helper function
            notification_count = 0
            for recipient in recipients:
                create_notification(
                    sender=request.user,
                    recipient=recipient,
                    subject=subject,
                    content=content,
                    notification_type="ADMIN",
                )
                notification_count += 1

            return render(
                request,
                "accounts/admin_notification_sent.html",
                {"recipient_count": notification_count},
            )
    else:
        form = AdminNotificationForm()

    return render(request, "accounts/admin_send_notification.html", {"form": form})


@login_required
def admin_sent_notifications(request):
    """
    View for administrators to see all notifications they have sent.
    Groups notifications by content and timestamp to avoid duplicates.
    """
    # Check if the current user is an admin
    if not request.user.is_staff:
        return HttpResponseForbidden(
            "You do not have permission to view sent notifications."
        )

    # Get all notifications sent by this admin
    sent_notifications = Notification.objects.filter(sender=request.user).order_by(
        "-created_at"
    )

    # Create a dictionary to group notifications manually
    notification_dict = {}

    for notification in sent_notifications:
        # Create a unique key using subject, content, and rounded timestamp (to the minute)
        timestamp_minute = notification.created_at.replace(second=0, microsecond=0)
        key = f"{notification.subject}|{notification.content}|{timestamp_minute}"

        if key not in notification_dict:
            notification_dict[key] = {
                "subject": notification.subject,
                "content": notification.content,
                "created_at": notification.created_at,
                "notification_type": notification.notification_type,
                "recipients": set(),
            }

        # Add recipient to the set
        notification_dict[key]["recipients"].add(notification.recipient)

    # Convert dictionary to list and add recipient counts
    notification_groups = []
    for data in notification_dict.values():
        recipients = list(data["recipients"])
        notification_groups.append(
            {
                "subject": data["subject"],
                "content": data["content"],
                "created_at": data["created_at"],
                "notification_type": data["notification_type"],
                "recipients": recipients[:5],  # First 5 recipients for display
                "recipient_count": len(recipients),
                "has_more_recipients": len(recipients) > 5,
            }
        )

    # Sort by created_at in descending order
    notification_groups.sort(key=lambda x: x["created_at"], reverse=True)

    return render(
        request,
        "accounts/admin_sent_notifications.html",
        {"notification_groups": notification_groups},
    )


@login_required
def debug_notification_counts(request):
    """
    Simple view to debug notification counts
    """
    unread_notifications = Notification.objects.filter(
        recipient=request.user, read=False
    )

    unread_messages = Message.objects.filter(
        recipient=request.user, read=False
    ).exclude(subject="Account Verification Approved")

    context = {
        "unread_notifications": unread_notifications,
        "unread_messages": unread_messages,
        "unread_notification_count": unread_notifications.count(),
        "unread_message_count": unread_messages.count(),
    }

    return render(request, "accounts/debug_counts.html", context)


def create_notification(
    sender, recipient, subject, content, notification_type="SYSTEM"
):
    """
    Helper function to create notifications ensuring they're marked as unread.
    This helps maintain consistency across the application.
    """
    return Notification.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        content=content,
        notification_type=notification_type,
        read=False,
    )  # Explicitly set to unread


def public_profile_view(request, username):
    # Get the user whose profile is being viewed

    profile_user = get_object_or_404(User, username=username)

    # Check if this is the user's own profile
    is_own_profile = request.user.username == username

    # If it's their own profile, redirect to the editable version
    if is_own_profile:
        return redirect("profile")

    # Get verification status from profile
    is_verified = hasattr(profile_user, "profile") and profile_user.profile.is_verified

    # Add this check for pending verification
    pending_verification = VerificationRequest.objects.filter(
        user=profile_user, status="PENDING"
    ).exists()

    # Calculate average rating across all listings
    from django.db.models import Avg
    from listings.models import Listing, Review

    # Get all listings by this user
    user_listings = Listing.objects.filter(user=profile_user)
    listing_count = user_listings.count()

    # Calculate the overall rating across all reviews from all listings
    average_rating = None
    total_reviews = 0

    if listing_count > 0 and is_verified:
        # Get all reviews for all listings by this user
        all_reviews = Review.objects.filter(listing__user=profile_user)
        total_reviews = all_reviews.count()

        if total_reviews > 0:
            # Calculate average rating across all reviews
            average_rating = all_reviews.aggregate(avg=Avg("rating"))["avg"]

    return render(
        request,
        "accounts/public_profile.html",
        {
            "profile_user": profile_user,
            "is_verified": is_verified,
            "average_rating": average_rating,
            "listing_count": listing_count,
            "review_count": total_reviews,
            "pending_verification": pending_verification,
        },
    )
