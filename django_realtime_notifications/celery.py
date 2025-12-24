import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_realtime_notifications.settings")

app = Celery("django_realtime_notifications")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    "cleanup-old-notifications": {
        "task": "notifications.tasks.cleanup_old_notifications",
        "schedule": crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    "send-email-digests": {
        "task": "notifications.tasks.send_email_digest",
        "schedule": crontab(hour=8, minute=0),  # Run daily at 8 AM
    },
}
