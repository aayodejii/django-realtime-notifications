from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .serializers import NotificationSerializer, NotificationStatsSerializer


class NotificationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.select_related("user").all()

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = request.query_params.get("priority")
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        user_filter = request.query_params.get("user")
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        paginator = PageNumberPagination()
        paginator.page_size = 50
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            notification = serializer.save(user=request.user)

            # Try immediate WebSocket delivery
            channel_layer = get_channel_layer()
            try:
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{notification.user.id}",
                    {
                        "type": "notification_message",
                        "notification": serializer.data
                    }
                )
                notification.mark_delivered()
            except Exception:
                # Queue for later delivery if WebSocket fails (user offline)
                from .tasks import process_offline_notification
                process_offline_notification.apply_async(
                    args=[notification.id],
                    countdown=60  # Retry after 1 minute
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.mark_read()
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)


class NotificationStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.select_related("user").all()

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = request.query_params.get("priority")
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        user_filter = request.query_params.get("user")
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        total = queryset.count()
        delivered = queryset.filter(status="delivered").count()
        read = queryset.filter(status="read").count()
        failed = queryset.filter(status="failed").count()
        pending = queryset.filter(status="pending").count()

        delivery_rate = (delivered / total * 100) if total > 0 else 0
        read_rate = (read / total * 100) if total > 0 else 0

        delivered_notifications = queryset.filter(
            status__in=["delivered", "read"], delivered_at__isnull=False
        )
        avg_latency = 0
        if delivered_notifications.exists():
            latencies = [
                (n.delivered_at - n.created_at).total_seconds()
                for n in delivered_notifications
            ]
            avg_latency = sum(latencies) / len(latencies)

        stats_data = {
            "total_notifications": total,
            "delivered_count": delivered,
            "read_count": read,
            "failed_count": failed,
            "pending_count": pending,
            "delivery_rate": round(delivery_rate, 2),
            "read_rate": round(read_rate, 2),
            "avg_delivery_latency": round(avg_latency, 3),
        }

        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)
