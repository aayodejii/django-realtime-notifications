import time
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle


class NotificationRateThrottle(SimpleRateThrottle):
    scope = "notifications"

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}


class PriorityBasedRateThrottle(SimpleRateThrottle):
    scope = "notifications_medium"

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        priority = request.data.get("priority", "medium")
        return self.cache_format % {"scope": f"notifications_{priority}", "ident": ident}

    def allow_request(self, request, view):
        priority = request.data.get("priority", "medium")
        rate_config = {
            "high": "100/hour",
            "medium": "50/hour",
            "low": "20/hour",
        }

        self.rate = rate_config.get(priority, "50/hour")
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return super().allow_request(request, view)


class RateLimiterService:
    @staticmethod
    def check_rate_limit(user_id, priority="medium", action="create"):
        rate_limits = {
            "high": {"create": 100, "window": 3600},
            "medium": {"create": 50, "window": 3600},
            "low": {"create": 20, "window": 3600},
        }

        config = rate_limits.get(priority, rate_limits["medium"])
        limit = config["create"]
        window = config["window"]

        cache_key = f"rate_limit:{action}:{priority}:{user_id}"
        current = cache.get(cache_key, 0)

        if current >= limit:
            return False, 0

        cache.set(cache_key, current + 1, window)
        remaining = limit - (current + 1)
        return True, remaining

    @staticmethod
    def get_remaining(user_id, priority="medium", action="create"):
        rate_limits = {
            "high": {"create": 100, "window": 3600},
            "medium": {"create": 50, "window": 3600},
            "low": {"create": 20, "window": 3600},
        }

        config = rate_limits.get(priority, rate_limits["medium"])
        limit = config["create"]

        cache_key = f"rate_limit:{action}:{priority}:{user_id}"
        current = cache.get(cache_key, 0)

        return max(0, limit - current)
