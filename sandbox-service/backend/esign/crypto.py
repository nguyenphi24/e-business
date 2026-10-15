"""CA và khóa ký giả lập bằng Ed25519. Chứng thư là JSON đơn giản do CA ký — không phải X.509 thật."""
import base64
import secrets
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.callbacks import canonical_json
from esign.models import CertificateAuthority, SignerCertificate

CA_NAME = "ProcureHub Sandbox CA (giả lập, không có giá trị pháp lý)"
CERT_VALIDITY = timedelta(days=365)


def _b64(raw):
	return base64.b64encode(raw).decode()


def _new_key():
	key = Ed25519PrivateKey.generate()
	pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
	public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
	return key, pem, _b64(public)


def _load(pem):
	return serialization.load_pem_private_key(pem.encode(), password=None)


def get_ca():
	ca = CertificateAuthority.objects.filter(name=CA_NAME).first()
	if ca:
		return ca
	_, pem, public = _new_key()
	try:
		with transaction.atomic():
			return CertificateAuthority.objects.create(name=CA_NAME, private_key_pem=pem, public_key=public)
	except IntegrityError:
		return CertificateAuthority.objects.get(name=CA_NAME)


def certificate_for(tax_code, name):
	"""Chứng thư của người ký theo mã số thuế; tạo mới (CA ký) nếu chưa có."""
	existing = SignerCertificate.objects.filter(tax_code=tax_code).first()
	if existing:
		return existing
	ca = get_ca()
	_, pem, public = _new_key()
	now = timezone.now()
	serial = secrets.token_hex(8).upper()
	certificate = {
		"serial": serial,
		"issuer": CA_NAME,
		"subject": {"tax_code": tax_code, "name": name},
		"algorithm": "Ed25519",
		"public_key": public,
		"valid_from": now.isoformat(),
		"valid_to": (now + CERT_VALIDITY).isoformat(),
	}
	ca_signature = _b64(_load(ca.private_key_pem).sign(canonical_json(certificate)))
	try:
		with transaction.atomic():
			return SignerCertificate.objects.create(
				tax_code=tax_code, name=name, serial=serial, private_key_pem=pem,
				certificate=certificate, ca_signature=ca_signature,
			)
	except IntegrityError:
		return SignerCertificate.objects.get(tax_code=tax_code)


def sign_hash(certificate, document_hash):
	"""Ký mã băm SHA-256 (hex) của tài liệu bằng khóa riêng của người ký."""
	return _b64(_load(certificate.private_key_pem).sign(bytes.fromhex(document_hash)))
