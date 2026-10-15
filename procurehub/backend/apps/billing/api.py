import json
import uuid

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.scope import get_scoped_querysets
from apps.audit.services import audit
from apps.billing import mock_provider
from apps.billing.models import Invoice, Payment
from apps.billing.serializers import InvoiceSerializer, PaymentCreateSerializer, PaymentSerializer, SimulateSerializer
from apps.billing.services import pending_amount, send_einvoice, start_gateway_payment
from apps.identity.permissions import IsAuthenticatedCompanyMember, has_any_role
from apps.integrations.client import is_enabled
from apps.procurement.models import IdempotencyKey
from common.exceptions import DomainError


def _invoice_response(invoice, request):
    invoice = Invoice.objects.select_related("purchase_order", "buyer_company", "supplier_company").prefetch_related(
        "payments"
    ).get(pk=invoice.pk)
    return InvoiceSerializer(invoice, context={"request": request}).data


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticatedCompanyMember]

    def get_queryset(self):
        queryset = get_scoped_querysets(self.request.user)["invoices"].select_related(
            "purchase_order", "buyer_company", "supplier_company"
        ).prefetch_related("payments").order_by("-issued_at")
        params = self.request.query_params
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("overdue") == "true":
            queryset = queryset.filter(status__in=Invoice.OPEN_STATUSES, due_date__lt=timezone.now().date())
        return queryset

    def _locked_object(self, pk):
        return get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the supplier can cancel an invoice.", status_code=403)
        with transaction.atomic():
            invoice = self._locked_object(pk)
            if invoice.supplier_company_id != request.user.company_id:
                raise DomainError("permission_denied", "This invoice does not belong to your company.", status_code=403)
            if invoice.status != Invoice.Status.ISSUED or invoice.payments.exclude(status=Payment.Status.FAILED).exists():
                raise DomainError("invalid_transition", "Only unpaid invoices without pending payments can be cancelled.")
            if invoice.einvoice_status in {Invoice.EInvoiceStatus.ISSUED, Invoice.EInvoiceStatus.PENDING_TAX_CODE}:
                raise DomainError("invalid_transition", "The e-invoice has been submitted to the tax authority; issue an adjustment invoice instead.")
            invoice.status = Invoice.Status.CANCELLED
            invoice.cancelled_at = timezone.now()
            invoice.save(update_fields=["status", "cancelled_at", "updated_at"])
            audit(request.user, "INVOICE_CANCELLED", invoice)
        return Response(_invoice_response(invoice, request))

    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        if not has_any_role(request.user, "FINANCE"):
            raise DomainError("permission_denied", "Only finance users can create payments.", status_code=403)
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise DomainError(
                "validation_error", "Idempotency-Key header is required.", status_code=422,
                field_errors={"Idempotency-Key": ["This header is required."]},
            )
        endpoint = f"/api/v1/invoices/{pk}/payments"
        existing = IdempotencyKey.objects.filter(key=idempotency_key, endpoint=endpoint, actor=request.user).first()
        if existing:
            return Response(existing.response_body, status=status.HTTP_200_OK)
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        with transaction.atomic():
            invoice = self._locked_object(pk)
            if invoice.buyer_company_id != request.user.company_id:
                raise DomainError("permission_denied", "This invoice does not belong to your company.", status_code=403)
            if invoice.status not in Invoice.OPEN_STATUSES:
                raise DomainError("invalid_transition", "Only open invoices can receive payments.")
            available = invoice.balance - pending_amount(invoice)
            if amount > available:
                raise DomainError(
                    "payment_exceeds_balance", "Payment amount exceeds the remaining balance.", status_code=422,
                    field_errors={"amount": [f"Must not exceed {available}."]},
                )
            payment = Payment.objects.create(
                invoice=invoice, amount=amount, external_ref=f"PAY-{uuid.uuid4().hex[:24]}", created_by=request.user,
                provider="SANDBOX_GW" if is_enabled() else "MOCK",
            )
            audit(request.user, "PAYMENT_CREATED", payment, {"invoice_id": str(invoice.id), "amount": str(amount), "provider": payment.provider})
        if payment.provider == "SANDBOX_GW":
            start_gateway_payment(payment)  # gọi mạng ngoài transaction
        body = json.loads(json.dumps({
            "payment": PaymentSerializer(payment).data,
            "invoice": _invoice_response(invoice, request),
        }, default=str))
        IdempotencyKey.objects.create(key=idempotency_key, endpoint=endpoint, actor=request.user, response_body=body)
        return Response(body, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def einvoice(self, request, pk=None):
        """Supplier phát hành lại (khi lỗi) hoặc làm mới trạng thái hóa đơn điện tử."""
        if not has_any_role(request.user, "SUPPLIER"):
            raise DomainError("permission_denied", "Only the supplier can submit an e-invoice.", status_code=403)
        if not is_enabled():
            raise DomainError("integration_unavailable", "E-invoice provider is not configured.", status_code=409)
        invoice = get_object_or_404(self.get_queryset(), pk=pk)
        if invoice.supplier_company_id != request.user.company_id:
            raise DomainError("permission_denied", "This invoice does not belong to your company.", status_code=403)
        if invoice.status == Invoice.Status.CANCELLED:
            raise DomainError("invalid_transition", "Cancelled invoices cannot be submitted.")
        send_einvoice(invoice, actor=request.user)
        return Response(_invoice_response(invoice, request))


class PaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticatedCompanyMember]

    def get_queryset(self):
        return get_scoped_querysets(self.request.user)["payments"].select_related("invoice")

    @action(detail=True, methods=["post"])
    def simulate(self, request, pk=None):
        if not settings.PAYMENT_SANDBOX_ENABLED:
            raise DomainError("sandbox_disabled", "Payment sandbox is disabled.", status_code=403)
        if not has_any_role(request.user, "FINANCE"):
            raise DomainError("permission_denied", "Only finance users can simulate payments.", status_code=403)
        serializer = SimulateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = get_object_or_404(self.get_queryset(), pk=pk)
        if payment.invoice.buyer_company_id != request.user.company_id:
            raise DomainError("permission_denied", "This payment does not belong to your company.", status_code=403)
        if payment.status != Payment.Status.PENDING:
            raise DomainError("invalid_transition", "Only pending payments can be simulated.")
        if payment.provider != "MOCK":
            raise DomainError("invalid_transition", "Gateway payments are completed on the payment gateway page.")
        result = mock_provider.simulate(payment, serializer.validated_data["outcome"])
        payment.refresh_from_db()
        return Response({"event": result, "invoice": _invoice_response(payment.invoice, request)})
