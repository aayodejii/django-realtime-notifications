from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "title",
        "priority",
        "status",
        "channel",
        "created_at",
        "delivered_at",
    ]
    list_filter = ["status", "priority", "channel", "created_at"]
    search_fields = ["title", "message", "user__username", "user__email"]
    readonly_fields = ["created_at", "delivered_at", "read_at", "last_attempt_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
