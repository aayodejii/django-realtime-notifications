import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        self.user_group_name = f"notifications_{self.user.id}"

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        missed_notifications = await self.get_missed_notifications()
        if missed_notifications:
            await self.send(text_data=json.dumps({
                "type": "missed_notifications",
                "notifications": missed_notifications
            }))

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event["notification"]
        }))

    @database_sync_to_async
    def get_missed_notifications(self):
        notifications = Notification.objects.filter(
            user=self.user,
            status="pending"
        ).order_by("-created_at")[:50]

        serializer = NotificationSerializer(notifications, many=True)
        return serializer.data
