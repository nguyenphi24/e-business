from decimal import Decimal

from django.db import models
from django.utils import timezone

from common.models import BaseModel


class Invoice(BaseModel):
    class Status(models.TextChoices):
        ISSUED = "ISSUED"
        PARTIALLY_PAID = "PARTIALLY_PAID"
        PAID = "PAID"
        CANCELLED = "CANCELLED"

    class EInvoiceStatus(models.TextChoices):
        NOT_SENT = "NOT_SENT"
        PENDING_TAX_CODE = "PENDING_TAX_CODE"
        ISSUED = "ISSUED"
        FAILED = "FAILED"

    OPEN_STATUSES = (Status.ISSUED, Status.PARTIALLY_PAID)

    number = models.CharField(max_length=20, unique=True)
    purchase_order = models.ForeignKey("purchase_orders.PurchaseOrder", on_delete=models.PROTECT, related_name="invoices")
    buyer_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT, related_name="+")
    supplier_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    currency = models.CharField(max_length=3, default="VND")
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))  # = tổng PO (trước thuế)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10"))
    vat_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=18, decimal_places=2)  # subtotal + vat_amount, số phải thanh toán
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    issued_at = models.DateTimeField()
    due_date = models.DateField()  # issued_at + PO.payment_term_days (Net N)
    issued_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")
    note = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    # Hóa đơn điện tử phát hành qua nhà cung cấp (sandbox-service)
    einvoice_status = models.CharField(max_length=20, choices=EInvoiceStatus.choices, default=EInvoiceStatus.NOT_SENT)
    einvoice_id = models.CharField(max_length=64, blank=True)
    einvoice_symbol = models.CharField(max_length=10, blank=True)
    einvoice_number = models.PositiveIntegerField(null=True, blank=True)
    einvoice_lookup_code = models.CharField(max_length=20, blank=True)
    einvoice_tax_code = models.CharField(max_length=40, blank=True)
    einvoice_lookup_url = models.URLField(max_length=500, blank=True)
    einvoice_xml_url = models.URLField(max_length=500, blank=True)
    einvoice_error = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "invoices"
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order"], condition=~models.Q(status="CANCELLED"), name="uniq_open_invoice_per_po"
            ),
            models.CheckConstraint(condition=models.Q(paid_amount__gte=0), name="invoice_paid_gte0"),
        ]
        indexes = [models.Index(fields=["buyer_company", "status"]), models.Index(fields=["supplier_company", "status"])]

    @property
    def balance(self):
        return self.total - self.paid_amount

    @property
    def is_overdue(self):
        # "Overdue" là thuộc tính suy ra, không phải trạng thái lưu (SRS mục 4.1)
        return self.status in self.OPEN_STATUSES and self.due_date < timezone.now().date()


class Payment(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=20, default="MOCK")  # MOCK: nút mô phỏng nội bộ; SANDBOX_GW: qua cổng
    external_ref = models.CharField(max_length=64, unique=True)
    gateway_transaction_id = models.CharField(max_length=64, blank=True)
    checkout_url = models.URLField(max_length=500, blank=True)
    created_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")
    settled_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "payments"
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_amount_gt0")]


class PaymentEvent(models.Model):
    """Sự kiện từ cổng thanh toán; `event_id` unique bảo đảm webhook idempotent (FR-PAY-04)."""

    event_id = models.CharField(max_length=100, unique=True)
    payment = models.ForeignKey(Payment, null=True, on_delete=models.PROTECT, related_name="events")
    status = models.CharField(max_length=10)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    duplicate_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "payment_events"
