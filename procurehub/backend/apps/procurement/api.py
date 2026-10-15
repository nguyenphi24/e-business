from decimal import Decimal, ROUND_HALF_UP
import json

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.services import audit
from apps.billing.serializers import InvoiceSerializer
from apps.billing.services import issue_invoice, send_einvoice
from apps.identity.models import Company
from apps.identity.permissions import IsBuyer, IsAuthenticatedCompanyMember, IsManager, has_any_role
from apps.procurement.models import (
    DocumentSequence,
    IdempotencyKey,
    PurchaseRequest,
    Quotation,
    QuotationLine,
    QuotationRevision,
    RFQ,
    RFQInvitation,
    RFQLine,
    SupplierSelection,
)
from apps.notifications.services import notify_event
from apps.procurement.esign import request_signature
from apps.procurement.scoring import FORMULA, NEUTRAL_RATING, score_quotations, validate_weights
from apps.procurement.serializers import (
    QuotationSerializer,
    QuotationUpdateSerializer,
    RFQCreateSerializer,
    RFQSerializer,
    SelectionCreateSerializer,
    SupplierSelectionSerializer,
    PurchaseRequestSerializer,
    PurchaseOrderSerializer,
)
from apps.purchase_orders.models import DeliveryRecord, PurchaseOrder, PurchaseOrderLine
from apps.suppliers.models import SupplierEvaluation, SupplierRelationship
from apps.suppliers.services import rating_summary
from common.exceptions import DomainError


def validated_weights_or_422(weights):
    try:
        return validate_weights(weights)
    except ValueError as exc:
        raise DomainError("validation_error", "Scoring weights are invalid.", status_code=422, field_errors=exc.args[0])


def build_scoring(rfq, quotations):
    """Khối `scoring` của bảng so sánh (FR-CMP-05)."""
    ratings = rating_summary(rfq.company_id, [quotation.supplier_company_id for quotation in quotations])
    by_id = {str(quotation.id): quotation for quotation in quotations}
    entries = [
        {
            "id": str(quotation.id),
            "total": quotation.total,
            "delivery_days": quotation.delivery_days,
            "payment_term_days": quotation.payment_term_days,
            "rating": ratings.get(quotation.supplier_company_id, {}).get("average"),
        }
        for quotation in quotations
    ]
    results = score_quotations(entries, rfq.scoring_weights)
    for item in results:
        quotation = by_id[item["quotation_id"]]
        rating = ratings.get(quotation.supplier_company_id, {})
        item["supplier"] = {"id": str(quotation.supplier_company_id), "legal_name": quotation.supplier_company.legal_name}
        item["rating_average"] = rating.get("average")
        item["rating_count"] = rating.get("count", 0)
    return {
        "weights": rfq.scoring_weights,
        "formula": FORMULA,
        "neutral_rating": NEUTRAL_RATING,
        "results": results,
    }


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseRequestSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "submit", "cancel"}:
            return [IsBuyer()]
        if self.action in {"approve", "reject"}:
            return [IsManager()]
        return [IsAuthenticatedCompanyMember()]

    def get_queryset(self):
        queryset = PurchaseRequest.objects.select_related("company", "requester", "decided_by").prefetch_related("lines")
        user = self.request.user
        if has_any_role(user, "SYSTEM_ADMIN") or user.is_superuser:
            return queryset
        if not user.company_id:
            return queryset.none()
        return queryset.filter(company_id=user.company_id)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise DomainError("permission_denied", "A company is required to create a purchase request.", status_code=403)
        with transaction.atomic():
            request = serializer.save(
                number=DocumentSequence.next_number("PR", timezone.now().year),
                company=user.company,
                requester=user,
            )
            audit(user, "PR_CREATED", request)

    def _locked_object(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.requester_id != request.user.id and not has_any_role(request.user, "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only the requester can edit this purchase request.", status_code=403)
        if instance.status not in {PurchaseRequest.Status.DRAFT, PurchaseRequest.Status.REJECTED}:
            raise DomainError("invalid_transition", "Only draft or rejected requests can be edited.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            audit(self.request.user, "PR_UPDATED", instance)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        with transaction.atomic():
            instance = self._locked_object(pk)
            if instance.status not in {PurchaseRequest.Status.DRAFT, PurchaseRequest.Status.REJECTED}:
                raise DomainError("invalid_transition", "Only draft or rejected requests can be submitted.")
            if not instance.lines.exists():
                raise DomainError(
                    "validation_error", "At least one line is required.", status_code=422,
                    field_errors={"lines": ["At least one line is required."]},
                )
            instance.status = PurchaseRequest.Status.PENDING_APPROVAL
            instance.decided_by = None
            instance.decided_at = None
            instance.submitted_at = timezone.now()
            instance.save(update_fields=["status", "decided_by", "decided_at", "submitted_at", "updated_at"])
            audit(request.user, "PR_SUBMITTED", instance)
            notify_event("PR_SUBMITTED", instance, actor=request.user)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        with transaction.atomic():
            instance = self._locked_object(pk)
            if instance.status != PurchaseRequest.Status.PENDING_APPROVAL:
                raise DomainError("invalid_transition", "Only pending requests can be approved.")
            if instance.requester_id == request.user.id:
                raise DomainError(
                    "separation_of_duties", "The requester cannot approve their own request.", status_code=403
                )
            instance.status = PurchaseRequest.Status.APPROVED
            instance.decided_by = request.user
            instance.decided_at = timezone.now()
            instance.decision_reason = request.data.get("reason", "")
            instance.save(update_fields=["status", "decided_by", "decided_at", "decision_reason", "updated_at"])
            audit(request.user, "PR_APPROVED", instance, {"reason": instance.decision_reason})
            notify_event("PR_APPROVED", instance, actor=request.user)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            raise DomainError(
                "validation_error", "Rejection reason is required.", status_code=422,
                field_errors={"reason": ["This field is required."]},
            )
        with transaction.atomic():
            instance = self._locked_object(pk)
            if instance.status != PurchaseRequest.Status.PENDING_APPROVAL:
                raise DomainError("invalid_transition", "Only pending requests can be rejected.")
            if instance.requester_id == request.user.id:
                raise DomainError(
                    "separation_of_duties", "The requester cannot reject their own request.", status_code=403
                )
            instance.status = PurchaseRequest.Status.REJECTED
            instance.decided_by = request.user
            instance.decided_at = timezone.now()
            instance.decision_reason = reason
            instance.save(update_fields=["status", "decided_by", "decided_at", "decision_reason", "updated_at"])
            audit(request.user, "PR_REJECTED", instance, {"reason": reason})
            notify_event("PR_REJECTED", instance, actor=request.user)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            instance = self._locked_object(pk)
            if instance.status not in {PurchaseRequest.Status.DRAFT, PurchaseRequest.Status.REJECTED}:
                raise DomainError("invalid_transition", "Only draft or rejected requests can be cancelled.")
            if instance.requester_id != request.user.id and not has_any_role(request.user, "COMPANY_ADMIN", "SYSTEM_ADMIN"):
                raise DomainError("permission_denied", "Only the requester or company admin can cancel this request.", status_code=403)
            instance.status = PurchaseRequest.Status.CANCELLED
            instance.save(update_fields=["status", "updated_at"])
            audit(request.user, "PR_CANCELLED", instance)
        return Response(self.get_serializer(instance).data)


class RFQViewSet(viewsets.ModelViewSet):
    serializer_class = RFQSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return RFQCreateSerializer
        return RFQSerializer

    def get_permissions(self):
        if self.action in {"create", "publish", "close", "cancel", "invitation", "selection", "scoring_weights"}:
            return [IsBuyer()]
        return [IsAuthenticatedCompanyMember()]

    def get_queryset(self):
        queryset = RFQ.objects.select_related("company", "request").prefetch_related(
            "lines", "invitations__supplier_company"
        )
        user = self.request.user
        if has_any_role(user, "SYSTEM_ADMIN") or user.is_superuser:
            return queryset
        if not user.company_id:
            return queryset.none()
        if has_any_role(user, "SUPPLIER"):
            return queryset.filter(invitations__supplier_company_id=user.company_id).distinct()
        return queryset.filter(company_id=user.company_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.company_id:
            raise DomainError("permission_denied", "A company is required to create an RFQ.", status_code=403)
        data = serializer.validated_data
        weights = validated_weights_or_422(data["scoring_weights"]) if "scoring_weights" in data else None
        deadline = data["deadline"]
        if deadline <= timezone.now():
            raise DomainError("validation_error", "Deadline must be in the future.", status_code=422, field_errors={"deadline": ["Must be in the future."]})
        purchase_request = get_object_or_404(
            PurchaseRequest.objects.prefetch_related("lines"), company_id=user.company_id, pk=data["request_id"]
        )
        if purchase_request.status != PurchaseRequest.Status.APPROVED:
            raise DomainError("invalid_transition", "Only approved purchase requests can create an RFQ.")

        supplier_ids = data["supplier_company_ids"]
        suppliers = list(Company.objects.filter(id__in=supplier_ids, company_type=Company.CompanyType.SUPPLIER))
        if len(suppliers) != len(supplier_ids):
            raise DomainError(
                "validation_error", "Every selected company must be a valid supplier.", status_code=422,
                field_errors={"supplier_company_ids": ["One or more suppliers are invalid."]},
            )
        active_ids = set(
            SupplierRelationship.objects.filter(
                buyer_company_id=user.company_id,
                supplier_company_id__in=supplier_ids,
                status=SupplierRelationship.Status.ACTIVE,
            ).values_list("supplier_company_id", flat=True)
        )
        if active_ids != set(supplier_ids):
            raise DomainError(
                "permission_denied", "Only active supplier relationships can be invited.", status_code=403,
                field_errors={"supplier_company_ids": ["One or more supplier relationships are not active."]},
            )

        with transaction.atomic():
            rfq = RFQ.objects.create(
                number=DocumentSequence.next_number("RFQ", timezone.now().year),
                company=user.company,
                request=purchase_request,
                title=data["title"],
                instructions=data["instructions"],
                deadline=deadline,
                **({"scoring_weights": weights} if weights else {}),
            )
            RFQLine.objects.bulk_create(
                [
                    RFQLine(
                        rfq=rfq,
                        source_line=line,
                        description=line.description,
                        quantity=line.quantity,
                        unit=line.unit,
                    )
                    for line in purchase_request.lines.all()
                ]
            )
            RFQInvitation.objects.bulk_create(
                [RFQInvitation(rfq=rfq, supplier_company=supplier) for supplier in suppliers]
            )
            audit(user, "RFQ_CREATED", rfq, {"supplier_count": len(suppliers)})
        return Response(RFQSerializer(rfq, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def _locked_object(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        with transaction.atomic():
            rfq = self._locked_object(pk)
            if rfq.status != RFQ.Status.DRAFT:
                raise DomainError("invalid_transition", "Only draft RFQs can be published.")
            if rfq.deadline <= timezone.now():
                raise DomainError("deadline_passed", "RFQ deadline must be in the future.")
            if rfq.invitations.count() < 2:
                raise DomainError("validation_error", "At least two suppliers must be invited.", status_code=422, field_errors={"invitations": ["At least two suppliers are required."]})
            rfq.status = RFQ.Status.OPEN
            rfq.published_at = timezone.now()
            rfq.save(update_fields=["status", "published_at", "updated_at"])
            audit(request.user, "RFQ_PUBLISHED", rfq)
            notify_event("RFQ_PUBLISHED", rfq, actor=request.user)
        return Response(RFQSerializer(rfq, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        with transaction.atomic():
            rfq = self._locked_object(pk)
            if rfq.status != RFQ.Status.OPEN:
                raise DomainError("invalid_transition", "Only open RFQs can be closed.")
            rfq.status = RFQ.Status.CLOSED
            rfq.save(update_fields=["status", "updated_at"])
            audit(request.user, "RFQ_CLOSED", rfq)
        return Response(RFQSerializer(rfq, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            rfq = self._locked_object(pk)
            if rfq.status not in {RFQ.Status.DRAFT, RFQ.Status.OPEN}:
                raise DomainError("invalid_transition", "Only draft or open RFQs can be cancelled.")
            rfq.status = RFQ.Status.CANCELLED
            rfq.save(update_fields=["status", "updated_at"])
            audit(request.user, "RFQ_CANCELLED", rfq)
        return Response(RFQSerializer(rfq, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="invitations")
    def invitation(self, request, pk=None):
        supplier_ids = request.data.get("supplier_company_ids", [])
        serializer = RFQCreateSerializer(data={
            "request_id": str(self.get_object().request_id),
            "title": "placeholder",
            "deadline": self.get_object().deadline,
            "supplier_company_ids": supplier_ids,
        })
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            rfq = self._locked_object(pk)
            if rfq.status != RFQ.Status.DRAFT:
                raise DomainError("invalid_transition", "Invitations can only be changed on draft RFQs.")
            active_ids = set(
                SupplierRelationship.objects.filter(
                    buyer_company_id=rfq.company_id,
                    supplier_company_id__in=supplier_ids,
                    status=SupplierRelationship.Status.ACTIVE,
                ).values_list("supplier_company_id", flat=True)
            )
            if active_ids != set(supplier_ids):
                raise DomainError("permission_denied", "Only active supplier relationships can be invited.", status_code=403)
            existing_ids = set(rfq.invitations.values_list("supplier_company_id", flat=True))
            new_ids = set(supplier_ids) - existing_ids
            companies = Company.objects.filter(id__in=new_ids, company_type=Company.CompanyType.SUPPLIER)
            RFQInvitation.objects.bulk_create([RFQInvitation(rfq=rfq, supplier_company=company) for company in companies])
            audit(request.user, "RFQ_INVITATIONS_UPDATED", rfq, {"added": len(new_ids)})
        return Response(RFQSerializer(rfq, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="scoring-weights")
    def scoring_weights(self, request, pk=None):
        weights = validated_weights_or_422(request.data.get("scoring_weights", request.data))
        with transaction.atomic():
            rfq = self._locked_object(pk)
            if rfq.status not in {RFQ.Status.DRAFT, RFQ.Status.OPEN, RFQ.Status.CLOSED}:
                raise DomainError("invalid_transition", "Scoring weights can only change before the RFQ is awarded.")
            previous = rfq.scoring_weights
            rfq.scoring_weights = weights
            rfq.save(update_fields=["scoring_weights", "updated_at"])
            audit(request.user, "RFQ_SCORING_WEIGHTS_UPDATED", rfq, {"from": previous, "to": weights})
        return Response(RFQSerializer(rfq, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def comparison(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "MANAGER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can compare quotations.", status_code=403)
        rfq = self.get_object()
        if rfq.status not in {RFQ.Status.CLOSED, RFQ.Status.AWARDED}:
            raise DomainError("invalid_transition", "Comparison is available only after the RFQ is closed.")
        quotations = list(rfq.quotations.filter(status__in=[Quotation.Status.SUBMITTED, Quotation.Status.AWARDED]).select_related("supplier_company").prefetch_related("lines__rfq_line"))
        return Response({
            "rfq": RFQSerializer(rfq, context={"request": request}).data,
            "quotations": QuotationSerializer(quotations, many=True, context={"request": request}).data,
            "scoring": build_scoring(rfq, quotations),
        })

    @action(detail=True, methods=["get", "post"])
    def quotation(self, request, pk=None):
        rfq = self.get_object()
        if request.method == "GET":
            quotation = get_object_or_404(Quotation.objects.filter(rfq=rfq, supplier_company_id=request.user.company_id).prefetch_related("lines__rfq_line"))
            if not has_any_role(request.user, "SUPPLIER"):
                raise DomainError("permission_denied", "Only suppliers can access their quotation.", status_code=403)
            return Response(QuotationSerializer(quotation, context={"request": request}).data)
        if not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only suppliers can create quotations.", status_code=403)
        if rfq.status != RFQ.Status.OPEN:
            raise DomainError("invalid_transition", "Quotation is available only while the RFQ is open.")
        if rfq.deadline <= timezone.now():
            raise DomainError("deadline_passed", "The RFQ deadline has passed.")
        invitation = get_object_or_404(RFQInvitation, rfq=rfq, supplier_company_id=request.user.company_id)
        if invitation.status in {RFQInvitation.Status.DECLINED, RFQInvitation.Status.EXPIRED}:
            raise DomainError("permission_denied", "This invitation is no longer active.", status_code=403)
        if Quotation.objects.filter(rfq=rfq, supplier_company_id=request.user.company_id).exists():
            raise DomainError("invalid_transition", "A quotation already exists for this supplier and RFQ.")
        serializer = QuotationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        line_data = {line["rfq_line_id"]: line for line in serializer.validated_data.pop("lines", [])}
        rfq_lines = list(rfq.lines.all())
        if not set(line_data).issubset({line.id for line in rfq_lines}):
            raise DomainError("validation_error", "Quotation lines must belong to this RFQ.", status_code=422, field_errors={"lines": ["Invalid RFQ line."]})
        with transaction.atomic():
            quotation = Quotation.objects.create(rfq=rfq, supplier_company=request.user.company, **serializer.validated_data)
            QuotationLine.objects.bulk_create(
                [
                    QuotationLine(
                        quotation=quotation,
                        rfq_line=rfq_line,
                        offered_quantity=line_data.get(rfq_line.id, {}).get("offered_quantity") or rfq_line.quantity,
                        unit_price=line_data.get(rfq_line.id, {}).get("unit_price"),
                        line_total=0,
                    )
                    for rfq_line in rfq_lines
                ]
            )
            invitation.status = RFQInvitation.Status.VIEWED
            invitation.viewed_at = timezone.now()
            invitation.save(update_fields=["status", "viewed_at", "updated_at"])
            audit(request.user, "QUOTATION_CREATED", quotation)
        return Response(QuotationSerializer(quotation, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def selection(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can propose a selection.", status_code=403)
        serializer = SelectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            rfq = self._locked_object(pk)
            if rfq.status != RFQ.Status.CLOSED:
                raise DomainError("invalid_transition", "Selection can only be proposed after the RFQ is closed.")
            quotation = get_object_or_404(Quotation, rfq=rfq, pk=serializer.validated_data["quotation_id"])
            if quotation.status != Quotation.Status.SUBMITTED:
                raise DomainError("validation_error", "Only submitted quotations can be selected.", status_code=422, field_errors={"quotation_id": ["Quotation is not selectable."]})
            candidates = list(rfq.quotations.filter(status=Quotation.Status.SUBMITTED).select_related("supplier_company"))
            scoring = build_scoring(rfq, candidates)
            selected_score = next(item for item in scoring["results"] if item["quotation_id"] == str(quotation.id))
            score_snapshot = json.loads(json.dumps({
                "weights": scoring["weights"],
                "selected": selected_score,
                "ranking": [
                    {"quotation_id": item["quotation_id"], "supplier": item["supplier"]["legal_name"], "total_score": item["total_score"], "rank": item["rank"]}
                    for item in scoring["results"]
                ],
            }, default=str))
            selection = SupplierSelection.objects.create(
                rfq=rfq,
                quotation=quotation,
                rationale=serializer.validated_data["rationale"],
                proposed_by=request.user,
                proposed_at=timezone.now(),
                score_snapshot=score_snapshot,
            )
            audit(request.user, "SELECTION_PROPOSED", selection, {"total_score": score_snapshot["selected"]["total_score"], "rank": selected_score["rank"]})
            notify_event("SELECTION_PROPOSED", selection, actor=request.user)
        return Response(SupplierSelectionSerializer(selection, context={"request": request}).data, status=status.HTTP_201_CREATED)


class QuotationViewSet(viewsets.ModelViewSet):
    serializer_class = QuotationSerializer
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return QuotationUpdateSerializer
        return QuotationSerializer

    def get_permissions(self):
        return [IsAuthenticatedCompanyMember()]

    def get_queryset(self):
        queryset = Quotation.objects.select_related("rfq", "supplier_company").prefetch_related("lines__rfq_line")
        user = self.request.user
        if has_any_role(user, "SYSTEM_ADMIN") or user.is_superuser:
            return queryset
        if not user.company_id:
            return queryset.none()
        if has_any_role(user, "SUPPLIER"):
            return queryset.filter(supplier_company_id=user.company_id)
        return queryset.filter(rfq__company_id=user.company_id).exclude(status=Quotation.Status.DRAFT)

    def create(self, request, *args, **kwargs):
        raise DomainError("invalid_transition", "Create quotations through the RFQ quotation endpoint.")

    def update(self, request, *args, **kwargs):
        quotation = self.get_object()
        if quotation.supplier_company_id != request.user.company_id or not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the quotation owner can edit a quotation.", status_code=403)
        if quotation.status != Quotation.Status.DRAFT:
            raise DomainError("invalid_transition", "Only draft quotations can be edited.")
        if quotation.rfq.status != RFQ.Status.OPEN or quotation.rfq.deadline <= timezone.now():
            raise DomainError("deadline_passed", "The RFQ is no longer accepting quotation edits.")
        serializer = self.get_serializer(quotation, data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        lines = serializer.validated_data.get("lines")
        if lines is not None:
            rfq_line_ids = set(quotation.rfq.lines.values_list("id", flat=True))
            if not {line["rfq_line_id"] for line in lines}.issubset(rfq_line_ids):
                raise DomainError("validation_error", "Quotation lines must belong to this RFQ.", status_code=422, field_errors={"lines": ["Invalid RFQ line."]})
        self.perform_update(serializer)
        return Response(QuotationSerializer(quotation, context={"request": request}).data)

    def _locked_object(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        with transaction.atomic():
            quotation = self._locked_object(pk)
            if quotation.supplier_company_id != request.user.company_id or not has_any_role(request.user, "SUPPLIER"):
                raise DomainError("permission_denied", "Only the quotation owner can submit a quotation.", status_code=403)
            if quotation.status != Quotation.Status.DRAFT:
                raise DomainError("invalid_transition", "Only draft quotations can be submitted.")
            if quotation.rfq.status != RFQ.Status.OPEN:
                raise DomainError("invalid_transition", "Only quotations for open RFQs can be submitted.")
            if quotation.rfq.deadline <= timezone.now():
                raise DomainError("deadline_passed", "The RFQ deadline has passed.")
            rfq_lines = {line.id: line for line in quotation.rfq.lines.all()}
            quotation_lines = list(quotation.lines.all())
            if set(line.rfq_line_id for line in quotation_lines) != set(rfq_lines):
                raise DomainError("validation_error", "Quotation must contain every RFQ line.", status_code=422, field_errors={"lines": ["Every RFQ line is required."]})
            total = Decimal("0")
            snapshot_lines = []
            for line in quotation_lines:
                rfq_line = rfq_lines[line.rfq_line_id]
                if line.unit_price is None:
                    raise DomainError("validation_error", "Every RFQ line needs a unit price.", status_code=422, field_errors={"lines": [f"Missing price for line {line.rfq_line_id}."]})
                if line.offered_quantity != rfq_line.quantity:
                    raise DomainError("validation_error", "Offered quantity must equal RFQ quantity.", status_code=422, field_errors={"lines": [f"Quantity mismatch for line {line.rfq_line_id}."]})
                line.line_total = (line.offered_quantity * line.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                line.save(update_fields=["line_total"])
                total += line.line_total
                snapshot_lines.append({"rfq_line_id": line.rfq_line_id, "offered_quantity": str(line.offered_quantity), "unit_price": str(line.unit_price), "line_total": str(line.line_total)})
            quotation.revision += 1
            quotation.total = total
            quotation.status = Quotation.Status.SUBMITTED
            quotation.save(update_fields=["revision", "total", "status", "updated_at"])
            QuotationRevision.objects.create(
                quotation=quotation,
                revision=quotation.revision,
                snapshot_json={"lines": snapshot_lines, "total": str(total), "delivery_days": quotation.delivery_days, "payment_terms": quotation.payment_terms, "payment_term_days": quotation.payment_term_days},
                submitted_by=request.user,
            )
            invitation = quotation.rfq.invitations.get(supplier_company_id=request.user.company_id)
            invitation.status = RFQInvitation.Status.QUOTED
            invitation.save(update_fields=["status", "updated_at"])
            audit(request.user, "QUOTATION_SUBMITTED", quotation, {"revision": quotation.revision, "total": str(total)})
            notify_event("QUOTATION_SUBMITTED", quotation, actor=request.user)
        return Response(QuotationSerializer(quotation, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        """NCC yêu cầu ký số revision hiện tại; trả về sign_url của dịch vụ ký để mở trang nhập OTP."""
        quotation = self.get_object()
        if quotation.supplier_company_id != request.user.company_id or not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the quotation owner can sign a quotation.", status_code=403)
        signature = request_signature(quotation, request.user)
        return Response({"id": str(signature.id), "status": signature.status, "revision": signature.revision, "sign_url": signature.sign_url})

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        with transaction.atomic():
            quotation = self._locked_object(pk)
            if quotation.supplier_company_id != request.user.company_id or not has_any_role(request.user, "SUPPLIER"):
                raise DomainError("permission_denied", "Only the quotation owner can revise a quotation.", status_code=403)
            if quotation.status != Quotation.Status.SUBMITTED:
                raise DomainError("invalid_transition", "Only submitted quotations can be revised.")
            if quotation.rfq.status != RFQ.Status.OPEN or quotation.rfq.deadline <= timezone.now():
                raise DomainError("deadline_passed", "The RFQ is no longer accepting revisions.")
            quotation.status = Quotation.Status.DRAFT
            quotation.save(update_fields=["status", "updated_at"])
            audit(request.user, "QUOTATION_REVISED", quotation)
        return Response(QuotationSerializer(quotation, context={"request": request}).data)


class SupplierSelectionViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSelectionSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action in {"approve", "reject"}:
            return [IsManager()]
        return [IsAuthenticatedCompanyMember()]

    def get_queryset(self):
        queryset = SupplierSelection.objects.select_related(
            "rfq", "quotation", "quotation__supplier_company", "proposed_by", "decided_by"
        )
        user = self.request.user
        if has_any_role(user, "SYSTEM_ADMIN") or user.is_superuser:
            return queryset
        if not user.company_id:
            return queryset.none()
        return queryset.filter(rfq__company_id=user.company_id)

    def create(self, request, *args, **kwargs):
        raise DomainError("invalid_transition", "Create selections through the RFQ selection endpoint.")

    def _locked_object(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        with transaction.atomic():
            selection = self._locked_object(pk)
            if selection.status != SupplierSelection.Status.PROPOSED:
                raise DomainError("invalid_transition", "Only proposed selections can be approved.")
            if selection.proposed_by_id == request.user.id:
                raise DomainError("separation_of_duties", "The proposer cannot approve their own selection.", status_code=403)
            if selection.rfq.status != RFQ.Status.CLOSED:
                raise DomainError("invalid_transition", "Selection can only be approved after the RFQ is closed.")
            selection.status = SupplierSelection.Status.APPROVED
            selection.decided_by = request.user
            selection.decided_at = timezone.now()
            selection.decision_reason = request.data.get("reason", "")
            selection.save(update_fields=["status", "decided_by", "decided_at", "decision_reason", "updated_at"])
            selection.rfq.status = RFQ.Status.AWARDED
            selection.rfq.save(update_fields=["status", "updated_at"])
            selection.quotation.status = Quotation.Status.AWARDED
            selection.quotation.save(update_fields=["status", "updated_at"])
            Quotation.objects.filter(rfq=selection.rfq, status=Quotation.Status.SUBMITTED).exclude(pk=selection.quotation_id).update(status=Quotation.Status.NOT_SELECTED)
            audit(request.user, "SELECTION_APPROVED", selection, {"reason": selection.decision_reason})
            audit(request.user, "RFQ_AWARDED", selection.rfq, {"quotation_id": str(selection.quotation_id)})
            notify_event("SELECTION_APPROVED", selection, actor=request.user)
        return Response(SupplierSelectionSerializer(selection, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            raise DomainError("validation_error", "Rejection reason is required.", status_code=422, field_errors={"reason": ["This field is required."]})
        with transaction.atomic():
            selection = self._locked_object(pk)
            if selection.status != SupplierSelection.Status.PROPOSED:
                raise DomainError("invalid_transition", "Only proposed selections can be rejected.")
            if selection.proposed_by_id == request.user.id:
                raise DomainError("separation_of_duties", "The proposer cannot reject their own selection.", status_code=403)
            selection.status = SupplierSelection.Status.REJECTED
            selection.decided_by = request.user
            selection.decided_at = timezone.now()
            selection.decision_reason = reason
            selection.save(update_fields=["status", "decided_by", "decided_at", "decision_reason", "updated_at"])
            audit(request.user, "SELECTION_REJECTED", selection, {"reason": reason})
            notify_event("SELECTION_REJECTED", selection, actor=request.user)
        return Response(SupplierSelectionSerializer(selection, context={"request": request}).data)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        return [IsAuthenticatedCompanyMember()]

    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related(
            "selection", "company", "supplier_company"
        ).prefetch_related("lines__deliveries")
        user = self.request.user
        if has_any_role(user, "SYSTEM_ADMIN") or user.is_superuser:
            return queryset
        if not user.company_id:
            return queryset.none()
        if has_any_role(user, "SUPPLIER"):
            return queryset.filter(supplier_company_id=user.company_id)
        return queryset.filter(company_id=user.company_id)

    def create(self, request, *args, **kwargs):
        raise DomainError("invalid_transition", "Generate a purchase order from an approved selection.")

    def _locked_object(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        if not has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can generate a purchase order.", status_code=403)
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise DomainError("validation_error", "Idempotency-Key header is required.", status_code=422, field_errors={"Idempotency-Key": ["This header is required."]})
        endpoint = "/api/v1/purchase-orders/generate"
        existing = IdempotencyKey.objects.filter(key=idempotency_key, endpoint=endpoint, actor=request.user).first()
        if existing:
            return Response(existing.response_body, status=status.HTTP_200_OK)
        selection_id = request.data.get("selection_id")
        if not selection_id:
            raise DomainError("validation_error", "selection_id is required.", status_code=422, field_errors={"selection_id": ["This field is required."]})

        with transaction.atomic():
            selection = get_object_or_404(
                SupplierSelection.objects.select_for_update(of=("self",)).select_related("rfq", "quotation", "quotation__supplier_company"),
                pk=selection_id,
                rfq__company_id=request.user.company_id,
            )
            if selection.status != SupplierSelection.Status.APPROVED:
                raise DomainError("invalid_transition", "Only approved selections can generate a purchase order.")
            if hasattr(selection, "purchase_order"):
                order = selection.purchase_order
            else:
                quotation = selection.quotation
                quotation_lines = list(quotation.lines.select_related("rfq_line").all())
                order = PurchaseOrder.objects.create(
                    number=DocumentSequence.next_number("PO", timezone.now().year),
                    selection=selection,
                    company=selection.rfq.company,
                    supplier_company=quotation.supplier_company,
                    status=PurchaseOrder.Status.DRAFT,
                    currency=selection.rfq.request.currency,
                    total=quotation.total,
                    delivery_days=quotation.delivery_days,
                    payment_terms=quotation.payment_terms,
                    payment_term_days=quotation.payment_term_days if quotation.payment_term_days is not None else 30,
                )
                PurchaseOrderLine.objects.bulk_create(
                    [
                        PurchaseOrderLine(
                            po=order,
                            description=line.rfq_line.description,
                            unit=line.rfq_line.unit,
                            quantity=line.offered_quantity,
                            unit_price=line.unit_price,
                            line_total=line.line_total,
                        )
                        for line in quotation_lines
                    ]
                )
                audit(request.user, "PO_GENERATED", order, {"selection_id": str(selection.id)})
            response_body = json.loads(json.dumps(PurchaseOrderSerializer(order, context={"request": request}).data, default=str))
            IdempotencyKey.objects.create(
                key=idempotency_key,
                endpoint=endpoint,
                actor=request.user,
                response_body=response_body,
            )
        return Response(response_body, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can issue a purchase order.", status_code=403)
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.status != PurchaseOrder.Status.DRAFT:
                raise DomainError("invalid_transition", "Only draft purchase orders can be issued.")
            order.status = PurchaseOrder.Status.ISSUED
            order.issued_at = timezone.now()
            order.save(update_fields=["status", "issued_at", "updated_at"])
            audit(request.user, "PO_ISSUED", order)
            notify_event("PO_ISSUED", order, actor=request.user)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        if not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the supplier can acknowledge a purchase order.", status_code=403)
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.supplier_company_id != request.user.company_id:
                raise DomainError("permission_denied", "This purchase order does not belong to your company.", status_code=403)
            if order.status != PurchaseOrder.Status.ISSUED:
                raise DomainError("invalid_transition", "Only issued purchase orders can be acknowledged.")
            order.status = PurchaseOrder.Status.ACKNOWLEDGED
            order.acknowledged_at = timezone.now()
            order.save(update_fields=["status", "acknowledged_at", "updated_at"])
            audit(request.user, "PO_ACKNOWLEDGED", order)
            notify_event("PO_ACKNOWLEDGED", order, actor=request.user)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        if not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the supplier can decline a purchase order.", status_code=403)
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            raise DomainError("validation_error", "Decline reason is required.", status_code=422, field_errors={"reason": ["This field is required."]})
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.supplier_company_id != request.user.company_id:
                raise DomainError("permission_denied", "This purchase order does not belong to your company.", status_code=403)
            if order.status != PurchaseOrder.Status.ISSUED:
                raise DomainError("invalid_transition", "Only issued purchase orders can be declined.")
            order.status = PurchaseOrder.Status.DECLINED
            order.decline_reason = reason
            order.declined_at = timezone.now()
            order.save(update_fields=["status", "decline_reason", "declined_at", "updated_at"])
            selection = order.selection
            selection.status = SupplierSelection.Status.REJECTED_BY_SUPPLIER
            selection.save(update_fields=["status", "updated_at"])
            selection.rfq.status = RFQ.Status.CLOSED
            selection.rfq.save(update_fields=["status", "updated_at"])
            selection.quotation.status = Quotation.Status.NOT_SELECTED
            selection.quotation.save(update_fields=["status", "updated_at"])
            Quotation.objects.filter(rfq=selection.rfq, status=Quotation.Status.NOT_SELECTED).exclude(pk=selection.quotation_id).update(status=Quotation.Status.SUBMITTED)
            audit(request.user, "PO_DECLINED", order, {"reason": reason})
            notify_event("PO_DECLINED", order, actor=request.user)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def deliveries(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can record delivery.", status_code=403)
        deliveries = request.data.get("lines", [])
        if not isinstance(deliveries, list) or not deliveries:
            raise DomainError("validation_error", "At least one delivery line is required.", status_code=422, field_errors={"lines": ["This field is required."]})
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.status not in {PurchaseOrder.Status.ISSUED, PurchaseOrder.Status.ACKNOWLEDGED, PurchaseOrder.Status.PARTIALLY_DELIVERED}:
                raise DomainError("invalid_transition", "This purchase order cannot receive delivery.")
            po_lines = {str(line.id): line for line in order.lines.all()}
            for item in deliveries:
                line = po_lines.get(str(item.get("po_line_id")))
                try:
                    quantity = Decimal(str(item.get("delivered_quantity")))
                except (TypeError, ValueError):
                    quantity = Decimal("0")
                if not line or quantity <= 0:
                    raise DomainError("validation_error", "Delivery line is invalid.", status_code=422, field_errors={"lines": ["Each delivery must contain a valid positive quantity."]})
                delivered = sum((record.delivered_quantity for record in line.deliveries.all()), Decimal("0"))
                if delivered + quantity > line.quantity:
                    raise DomainError("validation_error", "Delivered quantity cannot exceed ordered quantity.", status_code=422, field_errors={"lines": [f"Delivery exceeds quantity for line {line.id}."]})
                DeliveryRecord.objects.create(po_line=line, delivered_quantity=quantity, delivered_at=timezone.now(), recorded_by=request.user)
            refreshed_lines = list(order.lines.prefetch_related("deliveries").all())
            totals = [sum((record.delivered_quantity for record in line.deliveries.all()), Decimal("0")) for line in refreshed_lines]
            if all(total == line.quantity for line, total in zip(refreshed_lines, totals)):
                order.status = PurchaseOrder.Status.DELIVERED
                order.delivered_at = timezone.now()
            elif any(total > 0 for total in totals):
                order.status = PurchaseOrder.Status.PARTIALLY_DELIVERED
            order.save(update_fields=["status", "delivered_at", "updated_at"])
            audit(request.user, "PO_DELIVERY_RECORDED", order, {"lines": deliveries})
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can complete a purchase order.", status_code=403)
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.status != PurchaseOrder.Status.DELIVERED:
                raise DomainError("invalid_transition", "Only delivered purchase orders can be completed.")
            order.status = PurchaseOrder.Status.COMPLETED
            order.save(update_fields=["status", "updated_at"])
            audit(request.user, "PO_COMPLETED", order)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "MANAGER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can cancel a purchase order.", status_code=403)
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.status not in {PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.ISSUED, PurchaseOrder.Status.ACKNOWLEDGED}:
                raise DomainError("invalid_transition", "This purchase order cannot be cancelled.")
            supplier_was_informed = order.status != PurchaseOrder.Status.DRAFT
            order.status = PurchaseOrder.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])
            audit(request.user, "PO_CANCELLED", order)
            if supplier_was_informed:
                notify_event("PO_CANCELLED", order, actor=request.user)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def invoice(self, request, pk=None):
        if not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the supplier can issue an invoice.", status_code=403)
        note = str(request.data.get("note", "")).strip()
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.supplier_company_id != request.user.company_id:
                raise DomainError("permission_denied", "This purchase order does not belong to your company.", status_code=403)
            invoice = issue_invoice(order, request.user, note=note)
        send_einvoice(invoice, actor=request.user)  # gọi nhà cung cấp hóa đơn điện tử sau khi commit
        return Response(InvoiceSerializer(invoice, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def evaluation(self, request, pk=None):
        if not has_any_role(request.user, "BUYER", "MANAGER", "COMPANY_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can evaluate suppliers.", status_code=403)
        field_errors = {}
        scores = {}
        for field in ("quality_score", "delivery_score"):
            value = request.data.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                field_errors[field] = ["Must be an integer between 1 and 5."]
            else:
                scores[field] = value
        if field_errors:
            raise DomainError("validation_error", "Evaluation is invalid.", status_code=422, field_errors=field_errors)
        with transaction.atomic():
            order = self._locked_object(pk)
            if order.company_id != request.user.company_id:
                raise DomainError("permission_denied", "This purchase order does not belong to your company.", status_code=403)
            if order.status != PurchaseOrder.Status.COMPLETED:
                raise DomainError("invalid_transition", "Only completed purchase orders can be evaluated.")
            if SupplierEvaluation.objects.filter(purchase_order=order).exists():
                raise DomainError("invalid_transition", "This purchase order has already been evaluated.")
            evaluation = SupplierEvaluation.objects.create(
                purchase_order=order,
                buyer_company_id=order.company_id,
                supplier_company_id=order.supplier_company_id,
                evaluated_by=request.user,
                comment=str(request.data.get("comment", "")).strip(),
                **scores,
            )
            audit(request.user, "SUPPLIER_EVALUATED", evaluation, {"po_id": str(order.id), **scores})
        order.refresh_from_db()
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)
