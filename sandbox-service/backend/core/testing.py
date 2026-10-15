"""Tiện ích test: bắt callback gửi đi thay vì gọi mạng thật."""
import json
from contextlib import contextmanager
from unittest import mock

from core.callbacks import SIGNATURE_HEADER, sign

API_HEADERS = {"HTTP_X_API_KEY": "test-api-key"}
TEST_SETTINGS = {
	"SANDBOX_API_KEY": "test-api-key",
	"SANDBOX_WEBHOOK_SECRET": "test-webhook-secret",
	"ALLOWED_CALLBACK_PREFIXES": ["http://merchant.test/"],
	"ALLOWED_RETURN_PREFIXES": ["http://shop.test/"],
	"PUBLIC_BASE_URL": "http://sandbox.test",
	"EINVOICE_TAX_DELAY_SECONDS": 0,
}


class _FakeResponse:
	status = 200

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False


@contextmanager
def capture_callbacks():
	sent = []

	def fake_urlopen(request, timeout=None):
		body = request.data
		sent.append({
			"url": request.full_url,
			"payload": json.loads(body),
			"signature_ok": request.get_header(SIGNATURE_HEADER.capitalize()) == sign(body),
		})
		return _FakeResponse()

	with mock.patch("core.callbacks.urllib.request.urlopen", side_effect=fake_urlopen):
		yield sent
