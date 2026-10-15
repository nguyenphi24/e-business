import uuid

from django.db import models


class CertificateAuthority(models.Model):
	"""CA gốc giả lập (một bản ghi). Khóa riêng lưu thẳng trong DB vì đây chỉ là sandbox."""

	name = models.CharField(max_length=100, unique=True)
	private_key_pem = models.TextField()
	public_key = models.CharField(max_length=64)  # base64 khóa công khai Ed25519 (32 byte)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "esign_ca"


class SignerCertificate(models.Model):
	tax_code = models.CharField(max_length=20, unique=True)
	name = models.CharField(max_length=255)
	serial = models.CharField(max_length=32, unique=True)
	private_key_pem = models.TextField()
	certificate = models.JSONField()  # nội dung chứng thư (subject, public_key, hiệu lực...)
	ca_signature = models.CharField(max_length=128)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "esign_certificates"


class SignRequest(models.Model):
	class Status(models.TextChoices):
		PENDING = "PENDING"
		SIGNED = "SIGNED"
		REJECTED = "REJECTED"
		LOCKED = "LOCKED"
		EXPIRED = "EXPIRED"

	MAX_ATTEMPTS = 3

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	external_ref = models.CharField(max_length=64, unique=True)
	signer_tax_code = models.CharField(max_length=20)
	signer_name = models.CharField(max_length=255)
	document_hash = models.CharField(max_length=64)
	document_label = models.CharField(max_length=255)
	callback_url = models.URLField(max_length=500)
	otp = models.CharField(max_length=6)
	attempts = models.PositiveSmallIntegerField(default=0)
	status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
	signature = models.CharField(max_length=128, blank=True)
	signed_at = models.DateTimeField(null=True, blank=True)
	expires_at = models.DateTimeField()
	last_event = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "esign_requests"
