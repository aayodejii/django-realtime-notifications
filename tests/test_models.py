import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from notifications.models import Notification

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestNotificationModel:
    def test_create_notification(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test Notification",
            message="Test message",
            priority="high",
        )

        assert notification.id is not None
        assert notification.user == user
        assert notification.title == "Test Notification"
        assert notification.message == "Test message"
        assert notification.priority == "high"
        assert notification.status == "pending"
        assert notification.channel == "websocket"
        assert notification.created_at is not None

    def test_mark_delivered(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test",
            message="Test",
            priority="medium",
        )

        notification.mark_delivered()

        assert notification.status == "delivered"
        assert notification.delivered_at is not None

    def test_mark_failed(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test",
            message="Test",
            priority="low",
        )

        notification.mark_failed("Connection timeout")

        assert notification.status == "failed"
        assert notification.failure_reason == "Connection timeout"
        assert notification.last_attempt_at is not None

    def test_mark_read(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test",
            message="Test",
        )

        notification.mark_read()

        assert notification.read_at is not None

    def test_notification_str(self, user):
        notification = Notification.objects.create(
            user=user,
            title="Test Notification",
            message="Test",
        )

        assert str(notification) == "testuser - Test Notification (pending)"

    def test_notification_ordering(self, user):
        notification1 = Notification.objects.create(
            user=user,
            title="First",
            message="Test",
        )

        notification2 = Notification.objects.create(
            user=user,
            title="Second",
            message="Test",
        )

        notifications = list(Notification.objects.all())
        assert notifications[0] == notification2
        assert notifications[1] == notification1

    def test_priority_choices(self, user):
        for priority in ["high", "medium", "low"]:
            notification = Notification.objects.create(
                user=user,
                title=f"{priority} priority",
                message="Test",
                priority=priority,
            )
            assert notification.priority == priority

    def test_channel_choices(self, user):
        for channel in ["websocket", "email", "both"]:
            notification = Notification.objects.create(
                user=user,
                title="Test",
                message="Test",
                channel=channel,
            )
            assert notification.channel == channel

    def test_data_field(self, user):
        test_data = {"key": "value", "count": 42}

        notification = Notification.objects.create(
            user=user,
            title="Test",
            message="Test",
            data=test_data,
        )

        assert notification.data == test_data
