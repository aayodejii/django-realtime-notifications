# Django Real-time Notifications

A scalable real-time notification system featuring WebSocket delivery, priority-based routing, rate limiting, offline processing, and comprehensive observability with Prometheus metrics and structured logging.

## Features

- Real-time WebSocket notifications
- Email notifications with fallback
- Priority-based delivery (high, medium, low)
- Rate limiting per priority level
- Connection management with device limits
- Offline notification processing
- Presence tracking
- Prometheus metrics and structured logging
- JWT authentication for WebSocket connections

## Tech Stack

- Django 6.0 & Django REST Framework
- Django Channels for WebSocket support
- Celery for async task processing
- PostgreSQL for persistent storage
- Redis for channel layer, caching, and presence tracking
- Prometheus for metrics collection
- Email backend for notifications

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd django-realtime-notifications
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- Database credentials
- Redis URL
- Email settings
- JWT secret key

4. Run migrations:
```bash
uv run python manage.py migrate
```

5. Create a superuser:
```bash
uv run python manage.py createsuperuser
```

## Running the Application

1. Start Redis:
```bash
docker run -d -p 6379:6379 --name redis-notifications redis:alpine
```

2. Start Celery worker:
```bash
uv run celery -A django_realtime_notifications worker --loglevel=info
```

3. Start Celery beat (for scheduled tasks):
```bash
uv run celery -A django_realtime_notifications beat --loglevel=info
```

4. Start Django development server:
```bash
uv run python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /api/auth/jwt/create/` - Get JWT token
- `POST /api/auth/jwt/refresh/` - Refresh JWT token

### Notifications
- `GET /api/notifications/` - List notifications (supports filtering)
- `POST /api/notifications/` - Create notification
- `GET /api/notifications/{id}/` - Get notification details
- `PATCH /api/notifications/{id}/` - Update notification
- `DELETE /api/notifications/{id}/` - Delete notification
- `PATCH /api/notifications/{id}/mark_read/` - Mark as read
- `GET /api/notifications/stats/` - Get notification statistics

### Metrics
- `GET /api/metrics/` - Prometheus metrics endpoint

## WebSocket Connection

Connect to WebSocket endpoint:
```
ws://localhost:8000/ws/notifications/?token=<JWT_TOKEN>
```

### Message Types

**Incoming:**
- `notification` - New notification
- `missed_notifications` - Notifications received while offline
- `pong` - Heartbeat response

**Outgoing:**
- `ping` - Heartbeat to maintain connection

## Frontend Demo

Open `frontend/index.html` in a browser to see the real-time notification demo.

Features:
- Real-time notification display
- Connection status indicator
- Disconnect/reconnect functionality
- Missed notification recovery
- Priority-based styling

## Rate Limits

- High priority: 100 requests/hour
- Medium priority: 50 requests/hour
- Low priority: 20 requests/hour

## Configuration

### Connection Limits
- Maximum 5 concurrent connections per user
- Configurable in `notifications/services/connection.py`

### Notification Channels
- `websocket` - Real-time delivery via WebSocket
- `email` - Email notification
- `both` - Both WebSocket and email

### Retry Strategy
- Failed notifications retry after 60 seconds
- Maximum delivery attempts tracked
- Exponential backoff for retries

## Monitoring

### Prometheus Metrics
Access metrics at `http://localhost:8000/api/metrics/`

Available metrics:
- `notifications_created_total` - Total notifications created
- `notifications_delivered_total` - Total notifications delivered
- `notifications_failed_total` - Total failed deliveries
- `notification_delivery_latency_seconds` - Delivery latency histogram
- `active_websocket_connections` - Current WebSocket connections
- `pending_notifications_count` - Pending notifications

### Structured Logging
Logs are output in JSON format for easy parsing by log aggregation tools.

## Development

Run tests:
```bash
uv run pytest
```

Check code style:
```bash
uv run ruff check .
```

Format code:
```bash
uv run ruff format .
```

## License

MIT
