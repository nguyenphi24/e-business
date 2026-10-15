import uuid

from django.db import models


class Transaction(models.Model):
	class Status(models.TextChoices):
		PENDING = "PENDING"
		SUCCEEDED = "SUCCEEDED"
		FAILED = "FAILED"
		CANCELLED = "CANCELLED"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	merchant_ref = models.CharField(max_length=64, unique=True)
	amount = models.DecimalField(max_digits=18, decimal_places=2)
	currency = models.CharField(max_length=3, default="VND")
	description = models.CharField(max_length=255, blank=True)
	return_url = models.URLField(max_length=500)
	ipn_url = models.URLField(max_length=500)
	status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
	bank_code = models.CharField(max_length=20, blank=True)
	last_event = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	completed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = "gateway_transactions"
