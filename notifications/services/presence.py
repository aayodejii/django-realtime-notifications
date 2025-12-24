import redis
from django.conf import settings

# Redis connection for presence tracking (using database 1 to separate from Celery)
redis_client = redis.Redis(host='127.0.0.1', port=6379, db=1, decode_responses=True)

PRESENCE_EXPIRY = 300  # 5 minutes


class PresenceService:
    """Service for tracking user online/offline status"""

    @staticmethod
    def mark_online(user_id):
        """Mark user as online in Redis with expiry"""
        redis_client.setex(f"user_presence:{user_id}", PRESENCE_EXPIRY, "online")

    @staticmethod
    def mark_offline(user_id):
        """Remove user from online presence"""
        redis_client.delete(f"user_presence:{user_id}")

    @staticmethod
    def is_online(user_id):
        """Check if user is currently online"""
        return redis_client.exists(f"user_presence:{user_id}") > 0

    @staticmethod
    def refresh_presence(user_id):
        """Refresh user's presence expiry (called on heartbeat/ping)"""
        if redis_client.exists(f"user_presence:{user_id}"):
            redis_client.expire(f"user_presence:{user_id}", PRESENCE_EXPIRY)

    @staticmethod
    def get_missed_notifications_cursor(user_id):
        """Get the last notification ID the user saw"""
        cursor = redis_client.get(f"user_cursor:{user_id}")
        return int(cursor) if cursor else 0

    @staticmethod
    def set_missed_notifications_cursor(user_id, notification_id):
        """Store the last notification ID the user saw"""
        redis_client.set(f"user_cursor:{user_id}", notification_id)
