from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Message
from .forms import MessageForm


@login_required
def inbox(request):
    messages_inbox = Message.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    context = {"messages_inbox": messages_inbox}
    return render(request, "messaging/inbox.html", context)


@login_required
def sent_messages(request):
    messages_sent = Message.objects.filter(sender=request.user).order_by("-created_at")
    context = {"messages_sent": messages_sent}
    return render(request, "messaging/sent_messages.html", context)


@login_required
def compose_message(request):
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            new_message = form.save(commit=False)
            new_message.sender = request.user
            new_message.save()
            return redirect("inbox")
    else:
        form = MessageForm()
    return render(request, "messaging/compose_message.html", {"form": form})


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
