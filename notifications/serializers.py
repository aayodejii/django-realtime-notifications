import bleach
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id"]


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "title",
            "message",
            "priority",
            "status",
            "channel",
            "created_at",
            "delivered_at",
            "read_at",
            "delivery_attempts",
            "last_attempt_at",
            "failure_reason",
            "data",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "delivered_at",
            "read_at",
            "delivery_attempts",
            "last_attempt_at",
        ]

    def validate_priority(self, value):
        valid_priorities = ["high", "medium", "low"]
        if value not in valid_priorities:
            raise serializers.ValidationError(
                f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
            )
        return value

    def validate_channel(self, value):
        valid_channels = ["websocket", "email", "both"]
        if value not in valid_channels:
            raise serializers.ValidationError(
                f"Invalid channel. Must be one of: {', '.join(valid_channels)}"
            )
        return value

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty")
        if len(value) > 255:
            raise serializers.ValidationError("Title cannot exceed 255 characters")
        return bleach.clean(value.strip(), tags=[], strip=True)

    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        if len(value) > 5000:
            raise serializers.ValidationError("Message cannot exceed 5000 characters")
        allowed_tags = ["b", "i", "u", "a", "p", "br"]
        allowed_attrs = {"a": ["href", "title"]}
        return bleach.clean(
            value.strip(), tags=allowed_tags, attributes=allowed_attrs, strip=True
        )


class NotificationStatsSerializer(serializers.Serializer):
    total_notifications = serializers.IntegerField()
    delivered_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    read_rate = serializers.FloatField()
    avg_delivery_latency = serializers.FloatField()
