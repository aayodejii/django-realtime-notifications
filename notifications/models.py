import logging
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from .middleware.metrics import (
    notifications_created_total,
    notifications_delivered_total,
    notifications_failed_total,
    notification_delivery_latency_seconds,
)

logger = logging.getLogger(__name__)


class Notification(models.Model):
    PRIORITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("delivered", "Delivered"),
        ("read", "Read"),
        ("failed", "Failed"),
    ]

    CHANNEL_CHOICES = [
        ("websocket", "WebSocket"),
        ("email", "Email"),
        ("both", "Both"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    channel = models.CharField(
        max_length=10, choices=CHANNEL_CHOICES, default="websocket"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    delivery_attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="notif_user_created_idx"),
            models.Index(
                fields=["status", "priority"], name="notif_status_priority_idx"
            ),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.status})"

    def mark_delivered(self):
        self.status = "delivered"
        self.delivered_at = timezone.now()
        self.save(update_fields=["status", "delivered_at"])

        notifications_delivered_total.labels(
            priority=self.priority, channel=self.channel
        ).inc()

        latency = (self.delivered_at - self.created_at).total_seconds()
        notification_delivery_latency_seconds.labels(priority=self.priority).observe(
            latency
        )

        logger.info(
            f"Notification {self.id} delivered to user {self.user_id} "
            f"(priority={self.priority}, latency={latency:.3f}s)"
        )

    def mark_read(self):
        self.status = "read"
        self.read_at = timezone.now()
        self.save(update_fields=["status", "read_at"])

    def mark_failed(self, reason):
        self.status = "failed"
        self.failure_reason = reason
        self.last_attempt_at = timezone.now()
        self.save(update_fields=["status", "failure_reason", "last_attempt_at"])

        notifications_failed_total.labels(priority=self.priority, reason=reason).inc()

        logger.error(
            f"Notification {self.id} failed for user {self.user_id} "
            f"(priority={self.priority}, reason={reason})"
        )

    def increment_attempts(self):
        self.delivery_attempts += 1
        self.last_attempt_at = timezone.now()
        self.save(update_fields=["delivery_attempts", "last_attempt_at"])
