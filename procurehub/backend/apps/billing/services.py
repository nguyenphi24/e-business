from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.audit.services import audit
from apps.billing.models import Invoice, Payment, PaymentEvent
from apps.integrations.client import IntegrationError, SandboxClient, callback_url, is_enabled
from apps.notifications.services import notify_event
from apps.procurement.models import DocumentSequence
from apps.purchase_orders.models import PurchaseOrder
from common.exceptions import DomainError

INVOICEABLE_PO_STATUSES = {PurchaseOrder.Status.DELIVERED, PurchaseOrder.Status.COMPLETED}
EVENT_STATUSES = {Payment.Status.SUCCEEDED, Payment.Status.FAILED}
VAT_RATE = Decimal("10")  # thuế suất GTGT áp dụng cho mọi hóa đơn (quyết định phạm vi demo)
CENT = Decimal("0.01")


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def issue_invoice(order, user, note=""):
    """Supplier lập hóa đơn cho PO đã giao (FR-INV-01, BR-18). Gọi bên trong transaction, PO đã được khóa."""
    if order.status not in INVOICEABLE_PO_STATUSES:
        raise DomainError("invalid_transition", "Invoices can only be issued for delivered or completed purchase orders.")
    if order.invoices.exclude(status=Invoice.Status.CANCELLED).exists():
        raise DomainError("invalid_transition", "This purchase order already has an active invoice.")
    issued_at = timezone.now()
    vat_amount = money(order.total * VAT_RATE / 100)
    invoice = Invoice.objects.create(
        number=DocumentSequence.next_number("INV", issued_at.year),
        purchase_order=order,
        buyer_company_id=order.company_id,
        supplier_company_id=order.supplier_company_id,
        currency=order.currency,
        subtotal=order.total,
        vat_rate=VAT_RATE,
        vat_amount=vat_amount,
        total=order.total + vat_amount,
        issued_at=issued_at,
        due_date=issued_at.date() + timedelta(days=order.payment_term_days),
        issued_by=user,
        note=note,
    )
    audit(user, "INVOICE_ISSUED", invoice, {"po_id": str(order.id), "due_date": str(invoice.due_date)})
    notify_event("INVOICE_ISSUED", invoice, actor=user)
    return invoice


def _einvoice_payload(invoice):
    order = invoice.purchase_order
    return {
        "external_ref": invoice.number,
        "seller": {"tax_code": invoice.supplier_company.tax_code, "name": invoice.supplier_company.legal_name},
        "buyer": {"tax_code": invoice.buyer_company.tax_code, "name": invoice.buyer_company.legal_name},
        "currency": invoice.currency,
        "issue_date": invoice.issued_at.date().isoformat(),
        "lines": [
            {"name": line.description, "unit": line.unit, "quantity": f"{line.quantity:.3f}",
             "unit_price": f"{line.unit_price:.2f}", "amount": f"{line.line_total:.2f}"}
            for line in order.lines.order_by("id")
        ],
        "subtotal": f"{invoice.subtotal:.2f}",
        "vat_rate": f"{invoice.vat_rate:.2f}",
        "vat_amount": f"{invoice.vat_amount:.2f}",
        "total": f"{invoice.total:.2f}",
        "callback_url": callback_url("/api/v1/webhooks/einvoice"),
    }


def _apply_einvoice_data(invoice, data):
    invoice.einvoice_id = data["einvoice_id"]
    invoice.einvoice_symbol = data["symbol"]
    invoice.einvoice_number = data["number"]
    invoice.einvoice_lookup_code = data["lookup_code"]
    invoice.einvoice_lookup_url = data["lookup_url"]
    invoice.einvoice_xml_url = data["xml_url"]
    invoice.einvoice_error = ""
    if data["status"] == "ISSUED":
        invoice.einvoice_status = Invoice.EInvoiceStatus.ISSUED
        invoice.einvoice_tax_code = data["tax_code"]
    else:
        invoice.einvoice_status = Invoice.EInvoiceStatus.PENDING_TAX_CODE


EINVOICE_FIELDS = [
    "einvoice_status", "einvoice_id", "einvoice_symbol", "einvoice_number", "einvoice_lookup_code",
    "einvoice_tax_code", "einvoice_lookup_url", "einvoice_xml_url", "einvoice_error", "updated_at",
]


def send_einvoice(invoice, actor=None):
    """Gửi hóa đơn sang nhà cung cấp hóa đơn điện tử. Gọi NGOÀI transaction vì có gọi mạng.

    Không kết nối được thì ghi FAILED để Supplier bấm gửi lại; hóa đơn nội bộ vẫn hợp lệ.
    """
    if not is_enabled() or invoice.status == Invoice.Status.CANCELLED:
        return invoice
    client = SandboxClient()
    try:
        if invoice.einvoice_id:
            data = client.get_einvoice(invoice.einvoice_id)
        else:
            data = client.create_einvoice(_einvoice_payload(invoice))
    except IntegrationError as exc:
        invoice.einvoice_status = Invoice.EInvoiceStatus.FAILED
        invoice.einvoice_error = str(exc)[:255]
        invoice.save(update_fields=["einvoice_status", "einvoice_error", "updated_at"])
        audit(actor, "EINVOICE_FAILED", invoice, {"error": invoice.einvoice_error})
        return invoice
    was_issued = invoice.einvoice_status == Invoice.EInvoiceStatus.ISSUED
    _apply_einvoice_data(invoice, data)
    invoice.save(update_fields=EINVOICE_FIELDS)
    if not was_issued:
        audit(actor, "EINVOICE_SUBMITTED", invoice, {"einvoice_id": invoice.einvoice_id, "status": invoice.einvoice_status})
        if invoice.einvoice_status == Invoice.EInvoiceStatus.ISSUED:
            notify_event("EINVOICE_ISSUED", invoice, actor=actor)
    return invoice


def apply_einvoice_event(event):
    """Callback "cơ quan thuế đã cấp mã" từ nhà cung cấp hóa đơn điện tử. Idempotent theo trạng thái."""
    required = ("external_ref", "einvoice_id", "status", "symbol", "number", "lookup_code", "lookup_url", "xml_url")
    if any(key not in event for key in required) or event["status"] != "ISSUED" or not event.get("tax_code"):
        raise DomainError("validation_error", "E-invoice event is invalid.", status_code=422)
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update(of=("self",)).filter(number=event["external_ref"]).first()
        if invoice is None:
            raise DomainError("not_found", "Invoice was not found.", status_code=404)
        if invoice.einvoice_status == Invoice.EInvoiceStatus.ISSUED:
            return {"external_ref": invoice.number, "ignored": True}
        _apply_einvoice_data(invoice, event)
        invoice.save(update_fields=EINVOICE_FIELDS)
        audit(None, "EINVOICE_ISSUED", invoice, {"source": "einvoice_provider", "tax_code": invoice.einvoice_tax_code})
        notify_event("EINVOICE_ISSUED", invoice)
    return {"external_ref": invoice.number, "ignored": False}


def start_gateway_payment(payment):
    """Tạo giao dịch ở cổng thanh toán; lỗi kết nối thì đánh dấu payment FAILED để không giữ chỗ số dư."""
    try:
        data = SandboxClient().create_payment(
            merchant_ref=payment.external_ref,
            amount=payment.amount,
            description=f"Thanh toán hóa đơn {payment.invoice.number}",
            return_url=f"{settings.FRONTEND_URL}/invoices?payment={payment.id}",
            ipn_url=callback_url("/api/v1/webhooks/payment"),
        )
    except IntegrationError as exc:
        payment.status = Payment.Status.FAILED
        payment.settled_at = timezone.now()
        payment.failure_reason = f"Không kết nối được cổng thanh toán: {exc}"[:255]
        payment.save(update_fields=["status", "settled_at", "failure_reason", "updated_at"])
        audit(None, "PAYMENT_FAILED", payment, {"source": "payment_gateway", "error": payment.failure_reason})
        return payment
    payment.gateway_transaction_id = data["transaction_id"]
    payment.checkout_url = data["checkout_url"]
    payment.save(update_fields=["gateway_transaction_id", "checkout_url", "updated_at"])
    return payment


def pending_amount(invoice):
    return invoice.payments.filter(status=Payment.Status.PENDING).aggregate(total=Sum("amount"))["total"] or Decimal("0")


def process_payment_event(event, source="webhook"):
    """Xử lý một sự kiện thanh toán; dùng chung cho webhook và nút mô phỏng (HLD mục 8).

    Idempotent theo `event_id`: lần thứ hai chỉ tăng `duplicate_count`, không đổi số dư.
    """
    event_id = str(event.get("event_id") or "").strip()
    external_ref = str(event.get("external_ref") or "").strip()
    status = str(event.get("status") or "").strip().upper()
    field_errors = {}
    if not event_id or len(event_id) > 100:
        field_errors["event_id"] = ["This field is required."]
    if not external_ref:
        field_errors["external_ref"] = ["This field is required."]
    if status not in EVENT_STATUSES:
        field_errors["status"] = ["Must be SUCCEEDED or FAILED."]
    if field_errors:
        raise DomainError("validation_error", "Payment event is invalid.", status_code=422, field_errors=field_errors)

    with transaction.atomic():
        try:
            with transaction.atomic():
                record = PaymentEvent.objects.create(
                    event_id=event_id,
                    status=status,
                    payload={"external_ref": external_ref, "status": status, "source": source},
                )
        except IntegrityError:
            PaymentEvent.objects.filter(event_id=event_id).update(duplicate_count=F("duplicate_count") + 1)
            existing = PaymentEvent.objects.select_related("payment").get(event_id=event_id)
            return {"event_id": event_id, "duplicate": True, "payment_status": existing.payment.status if existing.payment else None}

        payment = Payment.objects.select_for_update(of=("self",)).filter(external_ref=external_ref).first()
        if payment is None:
            raise DomainError("not_found", "Payment reference was not found.", status_code=404)
        invoice = Invoice.objects.select_for_update(of=("self",)).get(pk=payment.invoice_id)
        record.payment = payment
        record.save(update_fields=["payment"])

        if "amount" in event:
            try:
                reported = Decimal(str(event["amount"]))
            except (InvalidOperation, ValueError):
                reported = None
            if reported != payment.amount:
                raise DomainError("amount_mismatch", "Event amount does not match the payment.", status_code=422)

        if payment.status != Payment.Status.PENDING:
            return {"event_id": event_id, "duplicate": False, "ignored": True, "payment_status": payment.status}

        payment.status = status
        payment.settled_at = timezone.now()
        if status == Payment.Status.FAILED:
            payment.failure_reason = str(event.get("failure_reason") or "Mock provider declined the payment.")[:255]
        payment.save(update_fields=["status", "settled_at", "failure_reason", "updated_at"])

        if status == Payment.Status.SUCCEEDED:
            invoice.paid_amount += payment.amount
            invoice.status = Invoice.Status.PAID if invoice.paid_amount >= invoice.total else Invoice.Status.PARTIALLY_PAID
            invoice.save(update_fields=["paid_amount", "status", "updated_at"])

        audit(None, f"PAYMENT_{status}", payment, {
            "source": source, "event_id": event_id, "invoice_id": str(invoice.id), "amount": str(payment.amount),
        })
        notify_event(f"PAYMENT_{status}", invoice)
        return {"event_id": event_id, "duplicate": False, "payment_status": payment.status}
