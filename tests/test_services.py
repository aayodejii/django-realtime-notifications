import pytest
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.services.priority import PriorityHandler
from notifications.services.presence import PresenceService
from notifications.services.rate_limiter import RateLimiterService

User = get_user_model()


class TestPriorityHandler:
    def test_get_ttl_high(self):
        ttl = PriorityHandler.get_ttl("high")
        assert ttl.total_seconds() == 3600

    def test_get_ttl_medium(self):
        ttl = PriorityHandler.get_ttl("medium")
        assert ttl.total_seconds() == 86400

    def test_get_ttl_low(self):
        ttl = PriorityHandler.get_ttl("low")
        assert ttl.total_seconds() == 604800

    def test_should_deliver_immediately_high(self):
        result = PriorityHandler.should_deliver_immediately("high")
        assert result is True

    def test_should_deliver_immediately_medium(self):
        result = PriorityHandler.should_deliver_immediately("medium")
        assert result is False

    def test_should_batch_low(self):
        result = PriorityHandler.should_batch("low")
        assert result is True

    def test_should_batch_high(self):
        result = PriorityHandler.should_batch("high")
        assert result is False


class TestPresenceService:
    @patch("notifications.services.presence.redis_client")
    def test_mark_online(self, mock_redis):
        PresenceService.mark_online(user_id=123)
        mock_redis.setex.assert_called_once()

    @patch("notifications.services.presence.redis_client")
    def test_mark_offline(self, mock_redis):
        PresenceService.mark_offline(user_id=123)
        mock_redis.delete.assert_called_once_with("user_presence:123")

    @patch("notifications.services.presence.redis_client")
    def test_is_online_true(self, mock_redis):
        mock_redis.exists.return_value = 1
        result = PresenceService.is_online(user_id=123)
        assert result is True

    @patch("notifications.services.presence.redis_client")
    def test_is_online_false(self, mock_redis):
        mock_redis.exists.return_value = 0
        result = PresenceService.is_online(user_id=123)
        assert result is False

    @patch("notifications.services.presence.redis_client")
    def test_refresh_presence(self, mock_redis):
        mock_redis.exists.return_value = 1
        PresenceService.refresh_presence(user_id=123)
        mock_redis.expire.assert_called_once()


class TestConnectionManagement:
    @patch("notifications.services.presence.redis_client")
    def test_add_connection_allowed(self, mock_redis):
        mock_redis.scard.return_value = 0

        result = PresenceService.add_connection(user_id=123, channel_name="test_channel")
        assert result is True
        mock_redis.sadd.assert_called_once()

    @patch("notifications.services.presence.redis_client")
    def test_add_connection_limit_reached(self, mock_redis):
        mock_redis.scard.return_value = 5

        result = PresenceService.add_connection(user_id=123, channel_name="new_channel")
        assert result is False

    @patch("notifications.services.presence.redis_client")
    def test_remove_connection(self, mock_redis):
        PresenceService.remove_connection(user_id=123, channel_name="test_channel")
        mock_redis.srem.assert_called_once()

    @patch("notifications.services.presence.redis_client")
    def test_get_connection_count(self, mock_redis):
        mock_redis.scard.return_value = 3
        count = PresenceService.get_connection_count(user_id=123)
        assert count == 3


class TestRateLimiter:
    @patch("notifications.services.rate_limiter.cache")
    def test_check_rate_limit_allowed(self, mock_cache):
        mock_cache.get.return_value = 0
        allowed, remaining = RateLimiterService.check_rate_limit(user_id=123, priority="high")
        assert allowed is True
        assert remaining == 99

    @patch("notifications.services.rate_limiter.cache")
    def test_check_rate_limit_denied(self, mock_cache):
        mock_cache.get.return_value = 100
        allowed, remaining = RateLimiterService.check_rate_limit(user_id=123, priority="high")
        assert allowed is False
        assert remaining == 0

    @patch("notifications.services.rate_limiter.cache")
    def test_get_remaining_high(self, mock_cache):
        mock_cache.get.return_value = 30
        remaining = RateLimiterService.get_remaining(user_id=123, priority="high")
        assert remaining == 70

    @patch("notifications.services.rate_limiter.cache")
    def test_get_remaining_medium(self, mock_cache):
        mock_cache.get.return_value = 20
        remaining = RateLimiterService.get_remaining(user_id=123, priority="medium")
        assert remaining == 30

    @patch("notifications.services.rate_limiter.cache")
    def test_get_remaining_low(self, mock_cache):
        mock_cache.get.return_value = 10
        remaining = RateLimiterService.get_remaining(user_id=123, priority="low")
        assert remaining == 10
