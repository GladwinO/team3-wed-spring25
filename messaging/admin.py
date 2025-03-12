# Register your models here.
from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "recipient", "subject", "created_at", "read")
    list_filter = ("read", "created_at")
    search_fields = ("sender__username", "recipient__username", "subject", "body")
