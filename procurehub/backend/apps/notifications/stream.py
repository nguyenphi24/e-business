"""Server-Sent Events cho thông báo (FR-NOTI-04).

View Django thuần (không qua DRF content negotiation). Xác thực bằng header Bearer giống REST;
frontend dùng fetch streaming thay vì EventSource để không phải đưa token lên URL.
"""
import json
import time

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Max
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.notifications.models import Notification
from apps.notifications.serializers import serialize_notification

BATCH_SIZE = 50


def _authenticate(request):
    try:
        result = JWTAuthentication().authenticate(request)
    except (InvalidToken, AuthenticationFailed):
        return None
    return result[0] if result else None


def _parse_last_id(request):
    raw = request.headers.get("Last-Event-ID") or request.GET.get("after")
    if raw is None or raw == "":
        return None
    try:
        return max(int(raw), 0)
    except ValueError:
        return None


def _format_event(notification):
    data = json.dumps(serialize_notification(notification), cls=DjangoJSONEncoder, ensure_ascii=False)
    return f"id: {notification.id}\nevent: notification\ndata: {data}\n\n"


def notification_stream(request):
    if request.method != "GET":
        return JsonResponse({"code": "method_not_allowed", "message": "Use GET.", "field_errors": {}}, status=405)
    user = _authenticate(request)
    if user is None:
        return JsonResponse(
            {"code": "authentication_required", "message": "Authentication credentials were not provided.", "field_errors": {}},
            status=401,
        )

    last_id = _parse_last_id(request)
    if last_id is None:
        # Kết nối mới không phát lại lịch sử; thông báo cũ lấy qua GET /notifications.
        last_id = Notification.objects.filter(recipient_id=user.id).aggregate(value=Max("id"))["value"] or 0
    max_seconds = settings.NOTIFICATION_STREAM_MAX_SECONDS
    poll_seconds = settings.NOTIFICATION_STREAM_POLL_SECONDS

    def events():
        nonlocal last_id
        started = time.monotonic()
        yield "retry: 3000\n\n"
        # Không tự đóng kết nối DB ở đây: Django đóng qua request_finished khi response streaming kết thúc.
        while True:
            batch = list(
                Notification.objects.filter(recipient_id=user.id, id__gt=last_id).order_by("id")[:BATCH_SIZE]
            )
            for notification in batch:
                last_id = notification.id
                yield _format_event(notification)
            if time.monotonic() - started >= max_seconds:
                break
            if not batch:
                yield ": ping\n\n"
            time.sleep(poll_seconds)

    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
