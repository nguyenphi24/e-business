import uuid

from django.db import models


class EInvoice(models.Model):
	class Status(models.TextChoices):
		PENDING_TAX_CODE = "PENDING_TAX_CODE"
		ISSUED = "ISSUED"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	external_ref = models.CharField(max_length=64, unique=True)
	# Ký hiệu cố ý có tiền tố SBX để không trùng định dạng hóa đơn điện tử thật.
	symbol = models.CharField(max_length=10)
	number = models.PositiveIntegerField()
	lookup_code = models.CharField(max_length=12, unique=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_TAX_CODE)
	tax_code = models.CharField(max_length=40, blank=True)
	seller_tax_code = models.CharField(max_length=20)
	seller_name = models.CharField(max_length=255)
	buyer_tax_code = models.CharField(max_length=20)
	buyer_name = models.CharField(max_length=255)
	currency = models.CharField(max_length=3, default="VND")
	subtotal = models.DecimalField(max_digits=18, decimal_places=2)
	vat_rate = models.DecimalField(max_digits=5, decimal_places=2)
	vat_amount = models.DecimalField(max_digits=18, decimal_places=2)
	total = models.DecimalField(max_digits=18, decimal_places=2)
	lines = models.JSONField(default=list)
	issue_date = models.DateField()
	callback_url = models.URLField(max_length=500)
	last_event = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	issued_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = "einvoices"
		constraints = [models.UniqueConstraint(fields=["symbol", "number"], name="uniq_einvoice_symbol_number")]
