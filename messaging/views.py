from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Message
from .forms import MessageForm
from django.contrib.auth import get_user_model


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
    messages_sent = Message.objects.filter(sender=request.user).order_by("-created_at")
    context = {"messages_sent": messages_sent}
    return render(request, "messaging/sent_messages.html", context)


@login_required
def compose_message(request, recipient_id=None):
    # Get owners whose listings the user has booked
    booked_owners = User.objects.filter(listing__booking__user=request.user).distinct()

    # Get users who have booked the user's listings
    booking_users = User.objects.filter(booking__listing__user=request.user).distinct()

    # Combine the lists and remove duplicates
    available_recipients = (
        (booked_owners | booking_users).exclude(id=request.user.id).distinct()
    )

    # If no recipients available and no specific recipient_id provided, redirect
    if not available_recipients.exists() and not recipient_id:
        request.session["error_message"] = (
            """You don't have any users to message yet. You need to either book
            a listing or have someone book your listing first."""
        )
        return redirect("inbox")

    initial_data = {}

    # If recipient_id is provided, get the user and pre-fill form
    if recipient_id:
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
        # Set the queryset before validation
        form.fields["recipient"].queryset = available_recipients
        if form.is_valid():
            recipient = form.cleaned_data["recipient"]

            # Verify recipient is in the allowed list
            if recipient in available_recipients or recipient.is_staff:
                new_message = form.save(commit=False)
                new_message.sender = request.user
                new_message.save()
                request.session["success_message"] = "Message sent successfully!"
                return redirect("inbox")
            else:
                form.add_error("recipient", "You cannot message this user.")
    else:
        # Create form with initial data if recipient is specified
        form = MessageForm(initial=initial_data)
        # Set the queryset for GET requests
        form.fields["recipient"].queryset = available_recipients

    context = {
        "form": form,
        "available_recipients": available_recipients,
    }
    return render(request, "messaging/compose_message.html", context)


@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, pk=message_id)

    # Only allow sender or recipient to view
    if message.recipient != request.user and message.sender != request.user:
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
