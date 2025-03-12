from .models import Message


def unread_messages_count(request):
    """
    Returns a dictionary with the count of unread messages for the logged-in user.
    This will be injected into every template (via settings).
    """
    if request.user.is_authenticated:
        count = Message.objects.filter(recipient=request.user, read=False).count()
        return {"unread_count": count}
    return {"unread_count": 0}
