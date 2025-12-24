import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .services.presence import PresenceService
from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_offline_notification(self, notification_id):
    """
    Retry delivery of notifications with exponential backoff.
    If all WebSocket attempts fail, send email notification.
    """
    try:
        notification = Notification.objects.get(id=notification_id)

        # Check if notification has exceeded retry attempts
        if notification.delivery_attempts >= 3:
            logger.info(
                f"Notification {notification_id} exceeded max retries, sending email fallback"
            )
            send_notification_email(notification)
            notification.mark_failed(
                "Exceeded max WebSocket retry attempts, sent via email"
            )
            return

        notification.increment_attempts()

        if not PresenceService.is_online(notification.user.id):
            logger.warning(f"User {notification.user.id} still offline, will retry")
            retry_delays = [60, 300, 900]
            retry_delay = retry_delays[
                min(notification.delivery_attempts - 1, len(retry_delays) - 1)
            ]
            raise self.retry(countdown=retry_delay)

        channel_layer = get_channel_layer()
        serializer = NotificationSerializer(notification)

        try:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{notification.user.id}",
                {"type": "notification_message", "notification": serializer.data},
            )
            notification.mark_delivered()
            logger.info(
                f"Notification {notification_id} delivered via WebSocket on retry"
            )
        except Exception as e:
            logger.warning(
                f"WebSocket delivery failed for notification {notification_id}: {str(e)}"
            )
            retry_delays = [60, 300, 900]
            retry_delay = retry_delays[
                min(notification.delivery_attempts - 1, len(retry_delays) - 1)
            ]
            raise self.retry(exc=e, countdown=retry_delay)

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as e:
        logger.error(
            f"Error processing offline notification {notification_id}: {str(e)}"
        )
        raise


def send_notification_email(notification):
    """Send notification via email as fallback"""
    try:
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=(
                settings.DEFAULT_FROM_EMAIL
                if hasattr(settings, "DEFAULT_FROM_EMAIL")
                else "noreply@example.com"
            ),
            recipient_list=[notification.user.email],
            fail_silently=False,
        )
        logger.info(f"Email sent for notification {notification.id}")
    except Exception as e:
        logger.error(
            f"Failed to send email for notification {notification.id}: {str(e)}"
        )


@shared_task
def send_email_digest():
    """
    Send daily email digest of unread notifications to users.
    Runs daily at 8 AM via Celery Beat.
    """
    # Find users with unread notifications from the last 24 hours
    yesterday = timezone.now() - timedelta(days=1)

    # Group notifications by user
    from django.db.models import Count

    users_with_unread = (
        Notification.objects.filter(
            status__in=["pending", "delivered"], created_at__gte=yesterday
        )
        .values("user")
        .annotate(count=Count("id"))
        .filter(count__gt=0)
    )

    for user_data in users_with_unread:
        user_id = user_data["user"]
        notification_count = user_data["count"]

        # Get user's unread notifications
        notifications = Notification.objects.filter(
            user_id=user_id,
            status__in=["pending", "delivered"],
            created_at__gte=yesterday,
        ).order_by("-created_at")[
            :10
        ]  # Limit to 10 most recent

        # Build email content
        message_lines = [
            f"You have {notification_count} unread notification(s):\n",
        ]

        for notif in notifications:
            message_lines.append(f"- {notif.title}: {notif.message}")

        message = "\n".join(message_lines)

        # Send digest email
        try:
            from users.models import User

            user = User.objects.get(id=user_id)
            send_mail(
                subject=f"Daily Notification Digest - {notification_count} unread",
                message=message,
                from_email=(
                    settings.DEFAULT_FROM_EMAIL
                    if hasattr(settings, "DEFAULT_FROM_EMAIL")
                    else "noreply@example.com"
                ),
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(
                f"Sent digest email to user {user_id} with {notification_count} notifications"
            )
        except Exception as e:
            logger.error(f"Failed to send digest email to user {user_id}: {str(e)}")


@shared_task
def cleanup_old_notifications():
    """
    Delete notifications older than 7 days (configurable by priority).
    Runs daily at 2 AM via Celery Beat.
    """
    now = timezone.now()

    # Different TTL based on priority
    ttl_config = {
        "high": timedelta(days=1),  # High priority: 1 day
        "medium": timedelta(days=7),  # Medium priority: 7 days
        "low": timedelta(days=30),  # Low priority: 30 days
    }

    total_deleted = 0

    for priority, ttl in ttl_config.items():
        cutoff_date = now - ttl
        deleted_count, _ = Notification.objects.filter(
            priority=priority,
            created_at__lt=cutoff_date,
            status="read",  # Only delete read notifications
        ).delete()

        total_deleted += deleted_count
        logger.info(
            f"Deleted {deleted_count} {priority} priority notifications older than {ttl.days} days"
        )

    logger.info(f"Cleanup complete: {total_deleted} total notifications deleted")
    return total_deleted
