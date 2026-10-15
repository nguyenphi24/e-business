from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.identity.permissions import IsAuthenticatedCompanyMember
from apps.notifications.models import Notification
from apps.notifications.serializers import serialize_notification


class NotificationViewSet(viewsets.ViewSet):
    """Hộp thư của user hiện tại; không bao giờ trả thông báo của user khác (NFR-SEC-05)."""

    permission_classes = [IsAuthenticatedCompanyMember]

    def _queryset(self, request):
        return Notification.objects.filter(recipient=request.user)

    def list(self, request):
        queryset = self._queryset(request)
        if request.query_params.get("unread") == "true":
            queryset = queryset.filter(read_at__isnull=True)
        try:
            limit = min(max(int(request.query_params.get("limit", "20")), 1), 100)
        except ValueError:
            limit = 20
        queryset = queryset.order_by("-id")
        return Response({
            "count": queryset.count(),
            "unread_count": self._queryset(request).filter(read_at__isnull=True).count(),
            "results": [serialize_notification(item) for item in queryset[:limit]],
        })

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread_count": self._queryset(request).filter(read_at__isnull=True).count()})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = get_object_or_404(self._queryset(request), pk=pk)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(serialize_notification(notification))

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self._queryset(request).filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})
