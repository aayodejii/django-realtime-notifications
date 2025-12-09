from django.urls import path
from .views import (
    NotificationListCreateView,
    NotificationDetailView,
    NotificationMarkReadView,
    NotificationStatsView,
)

urlpatterns = [
    path("notifications/", NotificationListCreateView.as_view(), name="notification-list"),
    path("notifications/<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
    path("notifications/<int:pk>/mark_read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("notifications/stats/", NotificationStatsView.as_view(), name="notification-stats"),
]
