import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .models import Notification
from .serializers import NotificationSerializer
from .services.presence import PresenceService

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

        allowed = await sync_to_async(PresenceService.add_connection)(
            self.user.id, self.channel_name
        )
        if not allowed:
            await self.accept()
            await self.close(code=4001)
            return

        await self.accept()

        await sync_to_async(PresenceService.mark_online)(self.user.id)

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

        if hasattr(self, "user") and not self.user.is_anonymous:
            await sync_to_async(PresenceService.remove_connection)(
                self.user.id, self.channel_name
            )
            connection_count = await sync_to_async(PresenceService.get_connection_count)(self.user.id)
            if connection_count == 0:
                await sync_to_async(PresenceService.mark_offline)(self.user.id)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "ping":
            await sync_to_async(PresenceService.refresh_presence)(self.user.id)
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
