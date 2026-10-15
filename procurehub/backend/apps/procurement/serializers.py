from decimal import Decimal

from rest_framework import serializers

from apps.procurement.models import (
    Quotation,
    QuotationLine,
    RFQ,
    RFQInvitation,
    RFQLine,
    PurchaseRequest,
    PurchaseRequestLine,
    SupplierSelection,
)
from apps.procurement.esign import signature_summary
from apps.purchase_orders.models import DeliveryRecord, PurchaseOrder, PurchaseOrderLine
from apps.suppliers.models import SupplierEvaluation


class PurchaseRequestLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseRequestLine
        fields = ["id", "description", "quantity", "unit"]
        read_only_fields = ["id"]

    def validate_quantity(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()

    def validate_unit(self, value):
        if not value.strip():
            raise serializers.ValidationError("Unit cannot be empty.")
        return value.strip()


class PurchaseRequestSerializer(serializers.ModelSerializer):
    lines = PurchaseRequestLineSerializer(many=True)
    requester = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequest
        fields = [
            "id", "number", "company", "requester", "status", "currency", "purpose", "needed_by",
            "estimated_budget", "submitted_at", "decided_by", "decided_at", "decision_reason",
            "created_at", "updated_at", "lines",
        ]
        read_only_fields = [
            "id", "number", "company", "requester", "status", "submitted_at", "decided_by", "decided_at",
            "decision_reason", "created_at", "updated_at",
        ]

    def validate_estimated_budget(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Estimated budget cannot be negative.")
        return value

    def get_requester(self, request):
        return {"id": str(request.requester_id), "email": request.requester.email, "full_name": request.requester.full_name}

    def get_company(self, request):
        return {"id": str(request.company_id), "legal_name": request.company.legal_name}

    def validate(self, attrs):
        lines = attrs.get("lines")
        if self.instance is None and not lines:
            raise serializers.ValidationError({"lines": ["At least one line is required."]})
        if lines is not None and not lines:
            raise serializers.ValidationError({"lines": ["At least one line is required."]})
        return attrs

    def create(self, validated_data):
        lines = validated_data.pop("lines")
        request = PurchaseRequest.objects.create(**validated_data)
        PurchaseRequestLine.objects.bulk_create(
            [PurchaseRequestLine(request=request, **line) for line in lines]
        )
        return request

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            PurchaseRequestLine.objects.bulk_create(
                [PurchaseRequestLine(request=instance, **line) for line in lines]
            )
        return instance


class RFQLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQLine
        fields = ["id", "description", "quantity", "unit", "source_line"]


class RFQInvitationSerializer(serializers.ModelSerializer):
    supplier = serializers.SerializerMethodField()

    class Meta:
        model = RFQInvitation
        fields = ["id", "supplier_company", "supplier", "status", "viewed_at", "responded_at", "decline_reason", "created_at"]

    def get_supplier(self, invitation):
        return {
            "id": str(invitation.supplier_company_id),
            "legal_name": invitation.supplier_company.legal_name,
            "category": invitation.supplier_company.category,
        }


class RFQSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()
    request = serializers.SerializerMethodField()
    lines = RFQLineSerializer(many=True, read_only=True)
    invitations = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            "id", "number", "company", "request", "title", "instructions", "status", "deadline",
            "scoring_weights", "published_at", "created_at", "updated_at", "lines", "invitations",
        ]

    def get_company(self, rfq):
        return {"id": str(rfq.company_id), "legal_name": rfq.company.legal_name}

    def get_request(self, rfq):
        return {"id": str(rfq.request_id), "number": rfq.request.number}

    def get_invitations(self, rfq):
        invitations = rfq.invitations.select_related("supplier_company").all()
        user = self.context.get("request").user if self.context.get("request") else None
        if user and user.company_id and user.roles.filter(role_code="SUPPLIER").exists():
            invitations = invitations.filter(supplier_company_id=user.company_id)
        return RFQInvitationSerializer(invitations, many=True, context=self.context).data


class RFQCreateSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    deadline = serializers.DateTimeField()
    supplier_company_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    scoring_weights = serializers.DictField(required=False)

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def validate_supplier_company_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Supplier list must not contain duplicates.")
        return value


class QuotationLineInputSerializer(serializers.Serializer):
    rfq_line_id = serializers.IntegerField()
    offered_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True)

    def validate_offered_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Offered quantity must be greater than zero.")
        return value

    def validate_unit_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value


class QuotationLineSerializer(serializers.ModelSerializer):
    rfq_line = serializers.SerializerMethodField()

    class Meta:
        model = QuotationLine
        fields = ["id", "rfq_line", "offered_quantity", "unit_price", "line_total"]

    def get_rfq_line(self, line):
        return {
            "id": line.rfq_line_id,
            "description": line.rfq_line.description,
            "quantity": line.rfq_line.quantity,
            "unit": line.rfq_line.unit,
        }


class QuotationSerializer(serializers.ModelSerializer):
    supplier = serializers.SerializerMethodField()
    rfq = serializers.SerializerMethodField()
    lines = QuotationLineSerializer(many=True, read_only=True)
    signature = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            "id", "rfq", "supplier", "status", "revision", "valid_until", "delivery_days",
            "payment_terms", "payment_term_days", "note", "total", "signature", "created_at", "updated_at", "lines",
        ]

    def get_supplier(self, quotation):
        return {"id": str(quotation.supplier_company_id), "legal_name": quotation.supplier_company.legal_name}

    def get_signature(self, quotation):
        request = self.context.get("request")
        is_owner = bool(request and request.user.company_id == quotation.supplier_company_id)
        return signature_summary(quotation, include_sign_url=is_owner)

    def get_rfq(self, quotation):
        return {"id": str(quotation.rfq_id), "number": quotation.rfq.number, "title": quotation.rfq.title}


class QuotationUpdateSerializer(serializers.Serializer):
    valid_until = serializers.DateField(required=False, allow_null=True)
    delivery_days = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True, max_length=255)
    payment_term_days = serializers.IntegerField(required=False, min_value=0, max_value=365, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)
    lines = QuotationLineInputSerializer(many=True, required=False)

    def validate(self, attrs):
        lines = attrs.get("lines")
        if lines is not None:
            line_ids = [line["rfq_line_id"] for line in lines]
            if len(line_ids) != len(set(line_ids)):
                raise serializers.ValidationError({"lines": ["RFQ lines must not be duplicated."]})
        return attrs

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            QuotationLine.objects.bulk_create(
                [
                    QuotationLine(
                        quotation=instance,
                        rfq_line_id=line["rfq_line_id"],
                        offered_quantity=line.get("offered_quantity") or 0,
                        unit_price=line.get("unit_price"),
                        line_total=0,
                    )
                    for line in lines
                ]
            )
        return instance


class SupplierSelectionSerializer(serializers.ModelSerializer):
    quotation = serializers.SerializerMethodField()
    proposed_by = serializers.SerializerMethodField()
    decided_by = serializers.SerializerMethodField()

    class Meta:
        model = SupplierSelection
        fields = [
            "id", "rfq", "quotation", "status", "rationale", "score_snapshot", "proposed_by", "proposed_at",
            "decided_by", "decided_at", "decision_reason", "created_at", "updated_at",
        ]

    def get_quotation(self, selection):
        return {
            "id": str(selection.quotation_id),
            "supplier_company_id": str(selection.quotation.supplier_company_id),
            "total": selection.quotation.total,
        }

    def get_proposed_by(self, selection):
        return {"id": str(selection.proposed_by_id), "email": selection.proposed_by.email}

    def get_decided_by(self, selection):
        if not selection.decided_by_id:
            return None
        return {"id": str(selection.decided_by_id), "email": selection.decided_by.email}


class SelectionCreateSerializer(serializers.Serializer):
    quotation_id = serializers.UUIDField()
    rationale = serializers.CharField()

    def validate_rationale(self, value):
        if not value.strip():
            raise serializers.ValidationError("Rationale cannot be empty.")
        return value.strip()


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    delivered_quantity = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderLine
        fields = ["id", "description", "unit", "quantity", "unit_price", "line_total", "delivered_quantity"]

    def get_delivered_quantity(self, line):
        return sum((delivery.delivered_quantity for delivery in line.deliveries.all()), Decimal("0"))


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier = serializers.SerializerMethodField()
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)
    invoice = serializers.SerializerMethodField()
    evaluation = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "number", "selection", "company", "supplier", "status", "currency", "total",
            "delivery_days", "payment_terms", "payment_term_days", "issued_at", "acknowledged_at",
            "delivered_at", "decline_reason", "declined_at", "created_at", "updated_at", "lines",
            "invoice", "evaluation",
        ]

    def get_supplier(self, order):
        return {"id": str(order.supplier_company_id), "legal_name": order.supplier_company.legal_name}

    def get_invoice(self, order):
        invoice = order.invoices.exclude(status="CANCELLED").first()
        if invoice is None:
            return None
        return {
            "id": str(invoice.id), "number": invoice.number, "status": invoice.status,
            "balance": invoice.balance, "due_date": invoice.due_date, "is_overdue": invoice.is_overdue,
        }

    def get_evaluation(self, order):
        # Đánh giá là dữ liệu nội bộ của bên mua (audit.scope: Supplier không thấy evaluations)
        request = self.context.get("request")
        if request and request.user.company_id == order.supplier_company_id:
            return None
        try:
            evaluation = order.evaluation
        except SupplierEvaluation.DoesNotExist:
            return None
        return {
            "quality_score": evaluation.quality_score,
            "delivery_score": evaluation.delivery_score,
            "comment": evaluation.comment,
            "created_at": evaluation.created_at,
        }
