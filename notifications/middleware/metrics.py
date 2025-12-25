from prometheus_client import Counter, Gauge, Histogram

notifications_created_total = Counter(
    "notifications_created_total",
    "Total number of notifications created",
    ["priority", "channel"],
)

notifications_delivered_total = Counter(
    "notifications_delivered_total",
    "Total number of notifications successfully delivered",
    ["priority", "channel"],
)

notifications_failed_total = Counter(
    "notifications_failed_total",
    "Total number of failed notification deliveries",
    ["priority", "reason"],
)

active_websocket_connections = Gauge(
    "active_websocket_connections", "Number of active WebSocket connections"
)

pending_notifications_count = Gauge(
    "pending_notifications_count", "Number of pending notifications"
)

notification_delivery_latency_seconds = Histogram(
    "notification_delivery_latency_seconds",
    "Time taken to deliver notifications",
    ["priority"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)
