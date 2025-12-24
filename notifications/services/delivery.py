import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .presence import PresenceService
from .priority import PriorityHandler

logger = logging.getLogger(__name__)


class NotificationDeliveryService:
    """Service for orchestrating notification delivery"""

    @staticmethod
    def deliver(notification, serializer_data):
        """
        Main delivery orchestration method.
        Checks user presence and routes to appropriate delivery method.
        """
        user_id = notification.user.id
        priority = notification.priority

        if PresenceService.is_online(user_id):
            return NotificationDeliveryService.deliver_via_websocket(
                user_id, serializer_data, notification
            )
        else:
            return NotificationDeliveryService.queue_for_later(notification)

    @staticmethod
    def deliver_via_websocket(user_id, serializer_data, notification):
        """
        Deliver notification via WebSocket with timeout.
        Returns True if successful, False otherwise.
        """
        channel_layer = get_channel_layer()

        try:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{user_id}",
                {
                    "type": "notification_message",
                    "notification": serializer_data
                }
            )
            notification.mark_delivered()
            logger.info(f"Notification {notification.id} delivered via WebSocket to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"WebSocket delivery failed for notification {notification.id}: {str(e)}")
            return False

    @staticmethod
    def queue_for_later(notification):
        """
        Queue notification for later delivery via Celery.
        """
        from notifications.tasks import process_offline_notification

        process_offline_notification.apply_async(
            args=[notification.id],
            countdown=60
        )
        logger.info(f"Notification {notification.id} queued for retry (user offline)")
        return False
