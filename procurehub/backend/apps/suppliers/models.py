from django.db import models

from common.models import BaseModel


class SupplierRelationship(BaseModel):
    class Status(models.TextChoices):
        INVITED = "INVITED"
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"
        BLOCKED = "BLOCKED"

    buyer_company = models.ForeignKey("identity.Company", on_delete=models.CASCADE, related_name="supplier_links")
    supplier_company = models.ForeignKey("identity.Company", on_delete=models.CASCADE, related_name="buyer_links")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INVITED)

    class Meta:
        db_table = "supplier_relationships"
        constraints = [
            models.UniqueConstraint(fields=["buyer_company", "supplier_company"], name="uniq_supplier_pair"),
        ]


class SupplierEvaluation(BaseModel):
    """Đánh giá NCC sau khi PO hoàn tất (FR-EVAL-01); dùng làm điểm uy tín khi chấm báo giá."""

    purchase_order = models.OneToOneField(
        "purchase_orders.PurchaseOrder", on_delete=models.PROTECT, related_name="evaluation"
    )
    buyer_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT, related_name="+")
    supplier_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT, related_name="+")
    quality_score = models.PositiveSmallIntegerField()
    delivery_score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    evaluated_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "supplier_evaluations"
        constraints = [
            models.CheckConstraint(condition=models.Q(quality_score__gte=1, quality_score__lte=5), name="eval_quality_1_5"),
            models.CheckConstraint(condition=models.Q(delivery_score__gte=1, delivery_score__lte=5), name="eval_delivery_1_5"),
        ]
        indexes = [models.Index(fields=["buyer_company", "supplier_company"])]
