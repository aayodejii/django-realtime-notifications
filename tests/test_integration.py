import pytest
from unittest.mock import patch
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from notifications.models import Notification
from django_realtime_notifications.asgi import application

User = get_user_model()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWebSocketFlow:
    async def test_websocket_reject_invalid_token(self):
        communicator = WebsocketCommunicator(
            application, "/ws/notifications/?token=invalid_token"
        )

        connected, _ = await communicator.connect()
        assert connected is False

    async def test_websocket_reject_no_token(self):
        communicator = WebsocketCommunicator(application, "/ws/notifications/")

        connected, _ = await communicator.connect()
        assert connected is False


@pytest.mark.django_db(transaction=True)
class TestNotificationDelivery:
    @patch("notifications.services.delivery.NotificationDeliveryService.deliver")
    def test_create_notification_via_api(self, mock_deliver, authenticated_client, user):
        response = authenticated_client.post(
            "/api/notifications/",
            {
                "title": "Test Notification",
                "message": "Test message",
                "priority": "high",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["title"] == "Test Notification"
        assert response.data["priority"] == "high"
        mock_deliver.assert_called_once()

    def test_list_notifications(self, authenticated_client, user):
        Notification.objects.create(
            user=user, title="Notification 1", message="Test 1"
        )
        Notification.objects.create(
            user=user, title="Notification 2", message="Test 2"
        )

        response = authenticated_client.get("/api/notifications/")

        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_mark_notification_read(self, authenticated_client, user):
        notification = Notification.objects.create(
            user=user, title="Test", message="Test"
        )

        response = authenticated_client.patch(f"/api/notifications/{notification.id}/mark_read/")

        assert response.status_code == 200
        notification.refresh_from_db()
        assert notification.read_at is not None

    def test_filter_by_priority(self, authenticated_client, user):
        Notification.objects.create(
            user=user, title="High", message="Test", priority="high"
        )
        Notification.objects.create(
            user=user, title="Low", message="Test", priority="low"
        )

        response = authenticated_client.get("/api/notifications/?priority=high")

        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["priority"] == "high"

    def test_filter_by_status(self, authenticated_client, user):
        notification = Notification.objects.create(
            user=user, title="Test", message="Test"
        )
        notification.mark_delivered()

        Notification.objects.create(user=user, title="Pending", message="Test")

        response = authenticated_client.get("/api/notifications/?status=delivered")

        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["status"] == "delivered"

    def test_get_notification_stats(self, authenticated_client, user):
        Notification.objects.create(
            user=user, title="Test 1", message="Test", priority="high"
        )
        Notification.objects.create(
            user=user, title="Test 2", message="Test", priority="medium"
        )

        response = authenticated_client.get("/api/notifications/stats/")

        assert response.status_code == 200
        assert "total_notifications" in response.data
        assert response.data["total_notifications"] == 2
