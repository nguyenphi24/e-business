import hashlib
import hmac
import json

from django.conf import settings

SIGNATURE_HEADER = "X-Sandbox-Signature"


def canonical_json(payload):
    """Cùng cách tuần tự hóa với sandbox-service; dùng cho chữ ký webhook và mã băm tài liệu."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


def sign(raw_body):
    return hmac.new(settings.SANDBOX_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()


def verify(raw_body, signature):
    return bool(signature) and hmac.compare_digest(sign(raw_body), signature)
