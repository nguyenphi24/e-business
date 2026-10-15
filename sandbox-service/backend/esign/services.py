import secrets
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.callbacks import deliver
from esign.crypto import certificate_for, sign_hash
from esign.models import SignRequest

REQUEST_TTL = timedelta(minutes=15)


def create_request(data):
	return SignRequest.objects.create(
		external_ref=data["external_ref"],
		signer_tax_code=data["signer"]["tax_code"],
		signer_name=data["signer"]["name"],
		document_hash=data["document_hash"],
		document_label=data["document_label"],
		callback_url=data["callback_url"],
		otp=f"{secrets.randbelow(1_000_000):06d}",
		expires_at=timezone.now() + REQUEST_TTL,
	)


def _finish(sign_request, status, extra):
	sign_request.status = status
	sign_request.last_event = {
		"event_id": f"evt_{uuid.uuid4().hex}",
		"external_ref": sign_request.external_ref,
		"request_id": str(sign_request.id),
		"status": status,
		"document_hash": sign_request.document_hash,
		**extra,
	}


def submit(sign_request_id, action, otp=""):
	"""Xử lý thao tác trên trang ký. Trả về (request, message lỗi hoặc '')."""
	with transaction.atomic():
		sign_request = SignRequest.objects.select_for_update().get(pk=sign_request_id)
		if sign_request.status != SignRequest.Status.PENDING:
			return sign_request, ""
		if sign_request.expires_at <= timezone.now():
			_finish(sign_request, SignRequest.Status.EXPIRED, {})
		elif action == "reject":
			_finish(sign_request, SignRequest.Status.REJECTED, {})
		elif action == "sign":
			if otp.strip() != sign_request.otp:
				sign_request.attempts += 1
				if sign_request.attempts < SignRequest.MAX_ATTEMPTS:
					sign_request.save(update_fields=["attempts"])
					return sign_request, f"OTP không đúng. Còn {SignRequest.MAX_ATTEMPTS - sign_request.attempts} lần thử."
				_finish(sign_request, SignRequest.Status.LOCKED, {})
			else:
				certificate = certificate_for(sign_request.signer_tax_code, sign_request.signer_name)
				sign_request.signature = sign_hash(certificate, sign_request.document_hash)
				sign_request.signed_at = timezone.now()
				_finish(sign_request, SignRequest.Status.SIGNED, {
					"signature": sign_request.signature,
					"signed_at": sign_request.signed_at.isoformat(),
					"certificate": {**certificate.certificate, "ca_signature": certificate.ca_signature},
				})
		else:
			return sign_request, "Thao tác không hợp lệ."
		sign_request.save()
	deliver("esign", sign_request.id, sign_request.callback_url, sign_request.last_event)
	return sign_request, ""
