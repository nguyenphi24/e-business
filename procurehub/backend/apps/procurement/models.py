from django.db import models, transaction

from common.models import BaseModel


def default_scoring_weights():
    # SRS FR-RFQ-07: giá 45, giao hàng 25, uy tín 20, điều khoản 10
    return {"price": 45, "delivery": 25, "rating": 20, "payment_terms": 10}


class DocumentSequence(models.Model):
    """Bộ đếm số chứng từ (D-09). Dùng next_number() trong transaction."""

    doc_type = models.CharField(max_length=10)
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "document_sequences"
        constraints = [models.UniqueConstraint(fields=["doc_type", "year"], name="uniq_doc_seq")]

    @classmethod
    def next_number(cls, doc_type, year):
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(doc_type=doc_type, year=year)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
            return f"{doc_type}-{year}-{seq.last_number:04d}"


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=100)
    endpoint = models.CharField(max_length=200)
    actor = models.ForeignKey("identity.User", on_delete=models.CASCADE)
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idempotency_keys"
        constraints = [models.UniqueConstraint(fields=["key", "endpoint", "actor"], name="uniq_idem")]


class PurchaseRequest(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        PENDING_APPROVAL = "PENDING_APPROVAL"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"
        CANCELLED = "CANCELLED"

    number = models.CharField(max_length=20, unique=True)
    company = models.ForeignKey("identity.Company", on_delete=models.PROTECT)
    requester = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="VND")
    purpose = models.TextField()
    needed_by = models.DateField()  # header (D-09)
    estimated_budget = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)  # FR-PR-07
    submitted_at = models.DateTimeField(null=True, blank=True)  # FR-PR-08
    decided_by = models.ForeignKey("identity.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)

    class Meta:
        db_table = "purchase_requests"
        indexes = [models.Index(fields=["company", "status"])]


class PurchaseRequestLine(models.Model):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=30)

    class Meta:
        db_table = "purchase_request_lines"
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="pr_line_qty_gt0")]


class RFQ(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        OPEN = "OPEN"
        CLOSED = "CLOSED"
        AWARDED = "AWARDED"
        CANCELLED = "CANCELLED"

    number = models.CharField(max_length=20, unique=True)
    company = models.ForeignKey("identity.Company", on_delete=models.PROTECT)
    request = models.ForeignKey(PurchaseRequest, on_delete=models.PROTECT, related_name="rfqs")
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    deadline = models.DateTimeField()  # UTC
    scoring_weights = models.JSONField(default=default_scoring_weights)  # FR-RFQ-07
    published_at = models.DateTimeField(null=True, blank=True)  # FR-RFQ-09

    class Meta:
        db_table = "rfqs"
        indexes = [models.Index(fields=["company", "status"]), models.Index(fields=["deadline"])]


class RFQLine(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="lines")
    source_line = models.ForeignKey(PurchaseRequestLine, null=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=30)

    class Meta:
        db_table = "rfq_lines"


class RFQInvitation(BaseModel):
    class Status(models.TextChoices):
        INVITED = "INVITED"
        VIEWED = "VIEWED"
        ACCEPTED = "ACCEPTED"  # NCC xác nhận tham gia báo giá
        QUOTED = "QUOTED"
        DECLINED = "DECLINED"
        EXPIRED = "EXPIRED"

    OPEN_STATUSES = (Status.INVITED, Status.VIEWED, Status.ACCEPTED)

    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="invitations")
    supplier_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INVITED)
    viewed_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)

    class Meta:
        db_table = "rfq_invitations"
        constraints = [models.UniqueConstraint(fields=["rfq", "supplier_company"], name="uniq_invitation")]


class Quotation(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        SUBMITTED = "SUBMITTED"
        AWARDED = "AWARDED"
        NOT_SELECTED = "NOT_SELECTED"

    rfq = models.ForeignKey(RFQ, on_delete=models.PROTECT, related_name="quotations")
    supplier_company = models.ForeignKey("identity.Company", on_delete=models.PROTECT)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    revision = models.PositiveIntegerField(default=0)  # tăng 1 mỗi lần submit (D-06)
    valid_until = models.DateField(null=True, blank=True)
    delivery_days = models.PositiveIntegerField(null=True, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    payment_term_days = models.PositiveIntegerField(null=True, blank=True)  # FR-QUO-08, số ngày công nợ
    note = models.TextField(blank=True)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0)  # trước VAT (D-05)

    class Meta:
        db_table = "quotations"
        constraints = [models.UniqueConstraint(fields=["rfq", "supplier_company"], name="uniq_quotation_per_supplier")]
        indexes = [models.Index(fields=["rfq", "status"])]


class QuotationLine(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="lines")
    rfq_line = models.ForeignKey(RFQLine, on_delete=models.PROTECT)
    offered_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    line_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        db_table = "quotation_lines"
        constraints = [
            models.UniqueConstraint(fields=["quotation", "rfq_line"], name="uniq_quotation_line"),
            models.CheckConstraint(
                condition=models.Q(unit_price__isnull=True) | models.Q(unit_price__gte=0), name="quo_price_gte0"
            ),
        ]


class QuotationRevision(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="revisions")
    revision = models.PositiveIntegerField()
    snapshot_json = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "quotation_revisions"
        constraints = [models.UniqueConstraint(fields=["quotation", "revision"], name="uniq_quotation_revision")]


class SupplierSelection(BaseModel):
    class Status(models.TextChoices):
        PROPOSED = "PROPOSED"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"
        REJECTED_BY_SUPPLIER = "REJECTED_BY_SUPPLIER"

    rfq = models.ForeignKey(RFQ, on_delete=models.PROTECT, related_name="selections")
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name="selections")
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PROPOSED)
    rationale = models.TextField()
    proposed_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")
    proposed_at = models.DateTimeField()
    decided_by = models.ForeignKey("identity.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    score_snapshot = models.JSONField(default=dict, blank=True)  # FR-CMP-06

    class Meta:
        db_table = "supplier_selections"
        constraints = [
            # một selection "đang sống" cho mỗi RFQ
            models.UniqueConstraint(
                fields=["rfq"],
                condition=models.Q(status__in=["PROPOSED", "APPROVED"]),
                name="uniq_active_selection_per_rfq",
            )
        ]


class QuotationSignature(BaseModel):
    """Chữ ký số của NCC trên một lần gửi (revision) báo giá, ký qua dịch vụ ký số từ xa."""

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SIGNED = "SIGNED"
        REJECTED = "REJECTED"
        FAILED = "FAILED"

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="signatures")
    revision = models.PositiveIntegerField()
    document_hash = models.CharField(max_length=64)  # SHA-256 của nội dung báo giá chuẩn hóa lúc yêu cầu ký
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    sign_request_id = models.CharField(max_length=64, blank=True)
    sign_url = models.URLField(max_length=500, blank=True)
    signature = models.CharField(max_length=128, blank=True)
    certificate = models.JSONField(default=dict, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    requested_by = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "quotation_signatures"
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "revision"],
                condition=models.Q(status__in=["PENDING", "SIGNED"]),
                name="uniq_live_signature_per_revision",
            )
        ]
