"""Xác minh chữ ký số: chứng thư do CA tin cậy cấp, còn hiệu lực lúc ký, và chữ ký khớp mã băm tài liệu."""
import base64
import hashlib
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from apps.integrations.client import IntegrationError, SandboxClient, is_enabled
from apps.integrations.models import TrustAnchor
from apps.integrations.security import canonical_json

SANDBOX_CA = "sandbox-ca"


def document_hash(document):
    return hashlib.sha256(canonical_json(document)).hexdigest()


def trusted_ca_key():
    anchor = TrustAnchor.objects.filter(name=SANDBOX_CA).first()
    if anchor:
        return anchor.public_key
    if not is_enabled():
        return None
    try:
        ca = SandboxClient().get_certificate_authority()
    except IntegrationError:
        return None
    anchor, _ = TrustAnchor.objects.get_or_create(name=SANDBOX_CA, defaults={"issuer": ca["issuer"], "public_key": ca["public_key"]})
    return anchor.public_key


def _verify_ed25519(public_key_b64, signature_b64, message):
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)).verify(base64.b64decode(signature_b64), message)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def verify_signature(expected_hash, signature, certificate, signed_at):
    """Trả về (True|False|None, lý do). None = chưa xác minh được (chưa có khóa CA tin cậy)."""
    ca_key = trusted_ca_key()
    if ca_key is None:
        return None, "Chưa có khóa CA tin cậy để xác minh."
    body = dict(certificate or {})
    ca_signature = body.pop("ca_signature", "")
    if not _verify_ed25519(ca_key, ca_signature, canonical_json(body)):
        return False, "Chứng thư không do CA tin cậy cấp."
    try:
        valid_from = datetime.fromisoformat(body["valid_from"])
        valid_to = datetime.fromisoformat(body["valid_to"])
    except (KeyError, ValueError):
        return False, "Chứng thư thiếu thời hạn hiệu lực."
    if signed_at is None or not valid_from <= signed_at <= valid_to:
        return False, "Chứng thư không còn hiệu lực tại thời điểm ký."
    if not _verify_ed25519(body.get("public_key", ""), signature, bytes.fromhex(expected_hash)):
        return False, "Chữ ký không khớp với mã băm tài liệu."
    return True, ""
