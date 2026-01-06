import pytest
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.serializers import NotificationSerializer

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestNotificationSerializer:
    def test_serialize_notification(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test Notification",
            message="Test message",
            priority="high",
        )

        serializer = NotificationSerializer(notification)
        data = serializer.data

        assert data["title"] == "Test Notification"
        assert data["message"] == "Test message"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert data["channel"] == "websocket"
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"

    def test_deserialize_notification(self, user):
        data = {
            "title": "New Notification",
            "message": "New message",
            "priority": "medium",
            "channel": "email",
        }

        serializer = NotificationSerializer(data=data)
        assert serializer.is_valid()

        notification = serializer.save(user=user)
        assert notification.title == "New Notification"
        assert notification.message == "New message"
        assert notification.priority == "medium"
        assert notification.channel == "email"
        assert notification.user == user

    def test_validate_priority(self):
        data = {
            "title": "Test",
            "message": "Test",
            "priority": "invalid_priority",
        }

        serializer = NotificationSerializer(data=data)
        assert not serializer.is_valid()
        assert "priority" in serializer.errors

    def test_validate_channel(self):
        data = {
            "title": "Test",
            "message": "Test",
            "channel": "invalid_channel",
        }

        serializer = NotificationSerializer(data=data)
        assert not serializer.is_valid()
        assert "channel" in serializer.errors

    def test_read_only_fields(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test",
            message="Test",
        )

        data = {
            "title": "Updated",
            "message": "Updated",
        }

        serializer = NotificationSerializer(notification, data=data, partial=True)
        assert serializer.is_valid()

        updated = serializer.save()
        assert updated.title == "Updated"
        assert updated.message == "Updated"

    def test_data_field_serialization(self, user):
        test_data = {"key": "value", "nested": {"count": 42}}

        notification = Notification.objects.create(
            user=user,
            title="Test",
            message="Test",
            data=test_data,
        )

        serializer = NotificationSerializer(notification)
        assert serializer.data["data"] == test_data
