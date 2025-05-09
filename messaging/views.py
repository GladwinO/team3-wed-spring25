from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Message
from .forms import MessageForm
from django.contrib.auth import get_user_model
from django import forms


User = get_user_model()


@login_required
def inbox(request):
    messages_inbox = Message.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )

    # Get session messages if any
    success_message = request.session.pop("success_message", None)
    error_message = request.session.pop("error_message", None)

    context = {
        "messages_inbox": messages_inbox,
        "success_message": success_message,
        "error_message": error_message,
    }
    return render(request, "messaging/inbox.html", context)


@login_required
def sent_messages(request):
    # Get all sent messages except verification requests
    messages_sent = (
        Message.objects.filter(sender=request.user)
        .exclude(
            subject="Verification Request"  # Hide verification requests from users
        )
        .order_by("-created_at")
    )

    context = {"messages_sent": messages_sent}
    return render(request, "messaging/sent_messages.html", context)


@login_required
def compose_message(request, recipient_id=None, admin_message=False):
    # Check if current user is an admin
    is_admin = request.user.is_staff

    # For admin messages to support, we need an admin user
    admin = None
    if admin_message:
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            request.session["error_message"] = "No admin users found in the system."
            return redirect("inbox")

    # Determine available recipients
    if is_admin:
        # Admins can message anyone
        available_recipients = User.objects.all().exclude(id=request.user.id)
    elif not admin_message:
        # Regular users can only message people they've had booking interactions with
        booked_owners = User.objects.filter(
            listing__booking__user=request.user
        ).distinct()
        booking_users = User.objects.filter(
            booking__listing__user=request.user
        ).distinct()
        available_recipients = (
            (booked_owners | booking_users).exclude(id=request.user.id).distinct()
        )

        # If no recipients available and no specific recipient_id provided, redirect
        if not available_recipients.exists() and not recipient_id:
            request.session["error_message"] = (
                "You don't have any users to message yet. You need to either book "
                "a listing or have someone book your listing first."
            )
            return redirect("inbox")
    else:
        # For admin support messages, no need to check available_recipients
        available_recipients = User.objects.filter(is_staff=True)

    # Prepare initial data
    initial_data = {}
    if admin_message:
        initial_data = {"subject": "Support Request: ", "recipient": admin.id}
    elif recipient_id:
        recipient = get_object_or_404(User, pk=recipient_id)
        # Check if recipient is in available_recipients or is an admin
        if recipient in available_recipients or recipient.is_staff:
            initial_data = {"recipient": recipient}
        else:
            request.session["error_message"] = (
                "You cannot message this user as you haven't had any booking interactions."
            )
            return redirect("inbox")

    if request.method == "POST":
        form = MessageForm(request.POST)

        # For admin messages, set recipient to admin
        if admin_message:
            form.data = form.data.copy()  # Make mutable copy
            form.data["recipient"] = admin.id  # Set recipient to admin ID
        else:
            # Regular message - set queryset for validation
            form.fields["recipient"].queryset = available_recipients

        if form.is_valid():
            new_message = form.save(commit=False)
            new_message.sender = request.user

            if admin_message:
                new_message.recipient = admin
                # Prefix subject for admin messages
                new_message.subject = f"[USER SUPPORT MESSAGE] {form.cleaned_data['subject'] or 'No Subject'}"
                success_msg = "Message sent to site administrators."
            else:
                success_msg = "Message sent successfully!"

            new_message.save()
            request.session["success_message"] = success_msg
            return redirect("inbox")
    else:
        # Create form with initial data
        form = MessageForm(initial=initial_data)

        if not admin_message:
            # Set the queryset for GET requests in regular messages
            form.fields["recipient"].queryset = available_recipients

    # For admin messages, hide the recipient field
    if admin_message:
        form.fields["recipient"].widget = forms.HiddenInput()

    context = {
        "form": form,
        "is_admin_message": admin_message,
        "available_recipients": available_recipients if not admin_message else None,
    }
    return render(request, "messaging/compose_message.html", context)


@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, pk=message_id)

    # Only allow sender, recipient or admin to view
    if (
        message.recipient != request.user
        and message.sender != request.user
        and not request.user.is_staff
    ):
        return HttpResponseForbidden("You are not allowed to view this message.")

    # If the current user is the recipient, mark as read
    if message.recipient == request.user and not message.read:
        message.read = True
        message.save()

    return render(request, "messaging/message_detail.html", {"message": message})


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, pk=message_id)

    # Only allow sender or recipient to delete
    if message.recipient != request.user and message.sender != request.user:
        return HttpResponseForbidden("You are not allowed to delete this message.")

    message.delete()
    return redirect("inbox")
