from django.urls import path
from prometheus_client import generate_latest
from django.http import HttpResponse
from .views import (
    NotificationListCreateView,
    NotificationDetailView,
    NotificationMarkReadView,
    NotificationStatsView,
)


def metrics_view(request):
    return HttpResponse(generate_latest(), content_type="text/plain")


urlpatterns = [
    path("notifications/", NotificationListCreateView.as_view(), name="notification-list"),
    path("notifications/<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
    path("notifications/<int:pk>/mark_read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("notifications/stats/", NotificationStatsView.as_view(), name="notification-stats"),
    path("metrics/", metrics_view, name="metrics"),
]
