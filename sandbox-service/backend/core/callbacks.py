"""Gửi callback có chữ ký về merchant. Dùng chung cho cổng thanh toán, hóa đơn điện tử và ký số."""
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from core.models import CallbackLog

SIGNATURE_HEADER = "X-Sandbox-Signature"
logger = logging.getLogger(__name__)


def canonical_json(payload):
	return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


def sign(raw_body):
	return hmac.new(settings.SANDBOX_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()


def is_allowed_callback(url):
	return any(url.startswith(prefix) for prefix in settings.ALLOWED_CALLBACK_PREFIXES)


def deliver(kind, object_id, url, payload):
	"""POST payload (JSON) tới url, ký HMAC. Trả về mã HTTP hoặc None nếu không gửi được.

	Không ném lỗi: merchant không nhận được thì sandbox vẫn giữ trạng thái, merchant có thể hỏi lại
	bằng API GET hoặc yêu cầu gửi lại.
	"""
	raw = canonical_json(payload)
	status_code, error = None, ""
	if not is_allowed_callback(url):
		error = "callback URL is not in ALLOWED_CALLBACK_PREFIXES"
	else:
		request = urllib.request.Request(
			url, data=raw, method="POST",
			headers={"Content-Type": "application/json", SIGNATURE_HEADER: sign(raw)},
		)
		try:
			with urllib.request.urlopen(request, timeout=settings.CALLBACK_TIMEOUT_SECONDS) as response:
				status_code = response.status
		except urllib.error.HTTPError as exc:
			status_code, error = exc.code, f"HTTP {exc.code}"
		except (urllib.error.URLError, TimeoutError, OSError) as exc:
			error = str(getattr(exc, "reason", exc))[:255]
	CallbackLog.objects.create(
		kind=kind, object_id=str(object_id), url=url, event_id=str(payload.get("event_id", "")),
		status_code=status_code, error=error,
	)
	if error:
		logger.warning("callback %s %s failed: %s", kind, object_id, error)
	return status_code
