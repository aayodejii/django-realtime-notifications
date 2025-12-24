import redis

# Redis connection for presence tracking (using database 1 to separate from Celery)
redis_client = redis.Redis(host="127.0.0.1", port=6379, db=1, decode_responses=True)

PRESENCE_EXPIRY = 300
MAX_CONNECTIONS_PER_USER = 5


class PresenceService:
    """Service for tracking user online/offline status"""

    @staticmethod
    def mark_online(user_id):
        redis_client.setex(f"user_presence:{user_id}", PRESENCE_EXPIRY, "online")

    @staticmethod
    def mark_offline(user_id):
        redis_client.delete(f"user_presence:{user_id}")

    @staticmethod
    def is_online(user_id):
        return redis_client.exists(f"user_presence:{user_id}") > 0

    @staticmethod
    def refresh_presence(user_id):
        if redis_client.exists(f"user_presence:{user_id}"):
            redis_client.expire(f"user_presence:{user_id}", PRESENCE_EXPIRY)

    @staticmethod
    def get_missed_notifications_cursor(user_id):
        cursor = redis_client.get(f"user_cursor:{user_id}")
        return int(cursor) if cursor else 0

    @staticmethod
    def set_missed_notifications_cursor(user_id, notification_id):
        redis_client.set(f"user_cursor:{user_id}", notification_id)

    @staticmethod
    def add_connection(user_id, channel_name):
        connections_key = f"user_connections:{user_id}"
        current_count = redis_client.scard(connections_key)

        if current_count >= MAX_CONNECTIONS_PER_USER:
            return False

        redis_client.sadd(connections_key, channel_name)
        redis_client.expire(connections_key, PRESENCE_EXPIRY)
        return True

    @staticmethod
    def remove_connection(user_id, channel_name):
        connections_key = f"user_connections:{user_id}"
        redis_client.srem(connections_key, channel_name)

    @staticmethod
    def get_connection_count(user_id):
        return redis_client.scard(f"user_connections:{user_id}")
