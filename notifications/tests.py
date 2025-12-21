from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Notification

User = get_user_model()


class NotificationModelTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_create_notification(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test",
            priority="high",
            channel="websocket",
        )
        self.assertEqual(notification.status, "pending")
        self.assertEqual(notification.delivery_attempts, 0)
        self.assertEqual(str(notification), "testuser - Test Notification (pending)")

    def test_mark_delivered(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test", priority="medium"
        )
        notification.mark_delivered()
        notification.refresh_from_db()
        self.assertEqual(notification.status, "delivered")
        self.assertIsNotNone(notification.delivered_at)

    def test_mark_read(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test", priority="low"
        )
        notification.mark_read()
        notification.refresh_from_db()
        self.assertEqual(notification.status, "read")
        self.assertIsNotNone(notification.read_at)

    def test_mark_failed(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test"
        )
        notification.mark_failed("Connection timeout")
        notification.refresh_from_db()
        self.assertEqual(notification.status, "failed")
        self.assertEqual(notification.failure_reason, "Connection timeout")

    def test_increment_attempts(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test"
        )
        notification.increment_attempts()
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_attempts, 1)
        self.assertIsNotNone(notification.last_attempt_at)


class NotificationAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notifications(self):
        Notification.objects.create(
            user=self.user, title="Test 1", message="Message 1", priority="high"
        )
        Notification.objects.create(
            user=self.user, title="Test 2", message="Message 2", priority="low"
        )

        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_create_notification_auto_user(self):
        data = {
            "title": "New Notification",
            "message": "New message",
            "priority": "medium",
            "channel": "websocket",
        }
        response = self.client.post("/api/notifications/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertEqual(notification.user, self.user)
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_create_notification_validation(self):
        data = {
            "title": "Test",
            "message": "Test",
            "priority": "invalid",
        }
        response = self.client.post("/api/notifications/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_notification_detail(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test", priority="high"
        )

        response = self.client.get(f"/api/notifications/{notification.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test")

    def test_update_notification(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test", priority="high"
        )

        data = {"title": "Updated Title"}
        response = self.client.patch(f"/api/notifications/{notification.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        notification.refresh_from_db()
        self.assertEqual(notification.title, "Updated Title")

    def test_delete_notification(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test", priority="high"
        )

        response = self.client.delete(f"/api/notifications/{notification.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Notification.objects.count(), 0)

    def test_mark_as_read(self):
        notification = Notification.objects.create(
            user=self.user, title="Test", message="Test", priority="high"
        )

        response = self.client.patch(f"/api/notifications/{notification.id}/mark_read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        notification.refresh_from_db()
        self.assertEqual(notification.status, "read")
        self.assertIsNotNone(notification.read_at)

    def test_filter_by_status(self):
        Notification.objects.create(
            user=self.user, title="Test 1", message="Message 1", status="pending"
        )
        Notification.objects.create(
            user=self.user, title="Test 2", message="Message 2", status="delivered"
        )

        response = self.client.get("/api/notifications/?status=pending")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_priority(self):
        Notification.objects.create(
            user=self.user, title="Test 1", message="Message 1", priority="high"
        )
        Notification.objects.create(
            user=self.user, title="Test 2", message="Message 2", priority="low"
        )

        response = self.client.get("/api/notifications/?priority=high")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_stats_endpoint(self):
        Notification.objects.create(
            user=self.user, title="Test 1", message="Test", status="pending"
        )
        n2 = Notification.objects.create(
            user=self.user, title="Test 2", message="Test", status="delivered"
        )
        n2.mark_delivered()
        n3 = Notification.objects.create(
            user=self.user, title="Test 3", message="Test", status="read"
        )
        n3.mark_read()

        response = self.client.get("/api/notifications/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_notifications"], 3)
        self.assertEqual(response.data["pending_count"], 1)
        self.assertEqual(response.data["delivered_count"], 1)
        self.assertEqual(response.data["read_count"], 1)

    def test_unauthenticated_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination(self):
        for i in range(60):
            Notification.objects.create(
                user=self.user, title=f"Test {i}", message="Test", priority="medium"
            )

        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 60)
        self.assertEqual(len(response.data["results"]), 50)
        self.assertIsNotNone(response.data["next"])
