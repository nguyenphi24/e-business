import logging
import time

from core.logging_utils import mask_query_string

logger = logging.getLogger("core.access")


class RequestLoggingMiddleware:
	"""Access log cho mọi request — KHÔNG log request/response body (dễ chứa
	field nhạy cảm ngoài danh sách mask cố định ở core/logging_utils.py).
	Query string nhạy cảm (token, apiKey, password...) bị che qua
	mask_query_string trước khi ra log.

	Thay cho access log mặc định của gunicorn (accesslog tắt trong
	gunicorn.conf.py) vì gunicorn ghi nguyên request line — không tự che
	được query string — và để access log giống hệt nhau giữa dev
	(runserver) và production (gunicorn). Xem
	repo conventions/stacks/django.md mục "Logging"."""

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		start = time.monotonic()
		response = self.get_response(request)
		duration_ms = int((time.monotonic() - start) * 1000)
		path = request.path
		if request.META.get("QUERY_STRING"):
			path = f"{path}?{mask_query_string(request.META['QUERY_STRING'])}"
		logger.info("%s %s %s %sms", request.method, path, response.status_code, duration_ms)
		return response
