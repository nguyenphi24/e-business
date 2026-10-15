from django.db import models

from common.models import BaseModel


class PurchaseOrder(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        ISSUED = "ISSUED"
        ACKNOWLEDGED = "ACKNOWLEDGED"
        DECLINED = "DECLINED"  # D-02
        PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED"
        DELIVERED = "DELIVERED"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"

    number = models.CharField(max_length=20, unique=True)
    selection = models.OneToOneField("procurement.SupplierSelection", on_delete=models.PROTECT, related_name="purchase_order")
    company = models.ForeignKey("identity.Company", on_delete=models.PROTECT, related_name="purchase_orders")
    supplier_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT, related_name="supplied_orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="VND")
    total = models.DecimalField(max_digits=18, decimal_places=2)
    delivery_days = models.PositiveIntegerField(null=True, blank=True)  # snapshot
    payment_terms = models.CharField(max_length=255, blank=True)  # snapshot
    payment_term_days = models.PositiveIntegerField(default=30)  # snapshot, Net N (BR-18)
    issued_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)  # khi giao đủ, dùng cho KPI giao đúng hạn

    class Meta:
        db_table = "purchase_orders"
        indexes = [models.Index(fields=["company", "status"]), models.Index(fields=["supplier_company", "status"])]


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=30)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    line_total = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "purchase_order_lines"


class DeliveryRecord(models.Model):
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.CASCADE, related_name="deliveries")
    delivered_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    delivered_at = models.DateTimeField()
    recorded_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "delivery_records"
        constraints = [models.CheckConstraint(condition=models.Q(delivered_quantity__gt=0), name="delivery_qty_gt0")]
