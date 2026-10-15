"""Ký số báo giá qua dịch vụ ký số từ xa và xác minh lại từ dữ liệu hiện tại trong DB.

Mã băm được tính trên nội dung báo giá chuẩn hóa. Khi xác minh, hệ thống tính lại mã băm từ dữ liệu đang
lưu: nếu ai đó sửa giá trực tiếp trong DB sau khi ký, mã băm lệch và chữ ký báo "không hợp lệ".
"""
from datetime import datetime

from django.db import transaction

from apps.audit.services import audit
from apps.integrations.client import IntegrationError, SandboxClient, callback_url, is_enabled
from apps.integrations.signatures import document_hash, verify_signature
from apps.notifications.services import notify_event
from apps.procurement.models import Quotation, QuotationSignature
from common.exceptions import DomainError


def quotation_document(quotation):
    lines = sorted(quotation.lines.select_related("rfq_line").all(), key=lambda line: line.rfq_line_id)
    return {
        "type": "QUOTATION",
        "rfq": quotation.rfq.number,
        "supplier_tax_code": quotation.supplier_company.tax_code,
        "revision": quotation.revision,
        "currency": quotation.rfq.request.currency,
        "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
        "delivery_days": quotation.delivery_days,
        "payment_term_days": quotation.payment_term_days,
        "payment_terms": quotation.payment_terms,
        "lines": [
            {
                "rfq_line_id": line.rfq_line_id,
                "description": line.rfq_line.description,
                "quantity": f"{line.offered_quantity:.3f}",
                "unit_price": f"{line.unit_price:.2f}" if line.unit_price is not None else None,
                "line_total": f"{line.line_total:.2f}",
            }
            for line in lines
        ],
        "total": f"{quotation.total:.2f}",
    }


def request_signature(quotation, user):
    """Tạo (hoặc trả lại) yêu cầu ký cho revision hiện tại. Gọi mạng nên chạy ngoài transaction."""
    if not is_enabled():
        raise DomainError("integration_unavailable", "E-signature provider is not configured.", status_code=409)
    if quotation.status != Quotation.Status.SUBMITTED:
        raise DomainError("invalid_transition", "Only submitted quotations can be signed.")
    live = quotation.signatures.filter(revision=quotation.revision, status__in=[QuotationSignature.Status.PENDING, QuotationSignature.Status.SIGNED]).first()
    if live:
        return live
    signature = QuotationSignature.objects.create(
        quotation=quotation, revision=quotation.revision, requested_by=user,
        document_hash=document_hash(quotation_document(quotation)),
    )
    supplier = quotation.supplier_company
    try:
        data = SandboxClient().create_sign_request(
            external_ref=str(signature.id),
            signer={"tax_code": supplier.tax_code, "name": supplier.legal_name},
            document_hash=signature.document_hash,
            document_label=f"Báo giá {quotation.rfq.number} – {supplier.legal_name} (lần gửi {quotation.revision})",
            callback=callback_url("/api/v1/webhooks/esign"),
        )
    except IntegrationError as exc:
        signature.status = QuotationSignature.Status.FAILED
        signature.failure_reason = str(exc)[:255]
        signature.save(update_fields=["status", "failure_reason", "updated_at"])
        raise DomainError("integration_error", "Cannot reach the e-signature provider.", status_code=502) from exc
    signature.sign_request_id = data["request_id"]
    signature.sign_url = data["sign_url"]
    signature.save(update_fields=["sign_request_id", "sign_url", "updated_at"])
    audit(user, "QUOTATION_SIGN_REQUESTED", quotation, {"revision": quotation.revision, "document_hash": signature.document_hash})
    return signature


def apply_sign_event(event):
    """Callback từ dịch vụ ký. Chỉ nhận chữ ký nếu chứng thư thuộc đúng NCC và chữ ký xác minh được."""
    if not event.get("external_ref") or not event.get("status"):
        raise DomainError("validation_error", "Sign event is invalid.", status_code=422)
    with transaction.atomic():
        signature = (
            QuotationSignature.objects.select_for_update(of=("self",))
            .select_related("quotation__supplier_company", "quotation__rfq")
            .filter(id=event["external_ref"]).first()
        )
        if signature is None:
            raise DomainError("not_found", "Signature request was not found.", status_code=404)
        if signature.status != QuotationSignature.Status.PENDING:
            return {"external_ref": str(signature.id), "ignored": True}
        quotation = signature.quotation
        if event["status"] == "SIGNED":
            certificate = event.get("certificate") or {}
            try:
                signed_at = datetime.fromisoformat(event.get("signed_at", ""))
            except ValueError:
                signed_at = None
            ok, reason = verify_signature(signature.document_hash, event.get("signature", ""), certificate, signed_at)
            subject = certificate.get("subject", {}).get("tax_code")
            if ok and subject != quotation.supplier_company.tax_code:
                ok, reason = False, "Chứng thư không thuộc nhà cung cấp gửi báo giá."
            if event.get("document_hash") != signature.document_hash:
                ok, reason = False, "Mã băm trong kết quả ký không khớp yêu cầu."
            if ok:
                signature.status = QuotationSignature.Status.SIGNED
                signature.signature = event["signature"]
                signature.certificate = certificate
                signature.signed_at = signed_at
            else:
                signature.status = QuotationSignature.Status.FAILED
                signature.failure_reason = reason or "Không xác minh được chữ ký."
        else:
            signature.status = QuotationSignature.Status.REJECTED
            signature.failure_reason = f"Yêu cầu ký kết thúc: {event['status']}"
        signature.save()
        audit(None, f"QUOTATION_SIGNATURE_{signature.status}", quotation, {
            "source": "esign_provider", "revision": signature.revision, "reason": signature.failure_reason,
        })
        if signature.status == QuotationSignature.Status.SIGNED:
            notify_event("QUOTATION_SIGNED", quotation)
    return {"external_ref": str(signature.id), "ignored": False, "status": signature.status}


def signature_summary(quotation, include_sign_url=False):
    """Trạng thái chữ ký của revision hiện tại: UNSIGNED, PENDING, VALID, INVALID, REJECTED, FAILED, UNVERIFIABLE."""
    signature = quotation.signatures.filter(revision=quotation.revision).order_by("-created_at").first()
    if signature is None:
        return {"state": "UNSIGNED"}
    base = {"revision": signature.revision, "requested_at": signature.created_at}
    if signature.status == QuotationSignature.Status.PENDING:
        return {**base, "state": "PENDING", **({"sign_url": signature.sign_url} if include_sign_url else {})}
    if signature.status != QuotationSignature.Status.SIGNED:
        return {**base, "state": signature.status, "reason": signature.failure_reason}
    subject = signature.certificate.get("subject", {})
    signed = {
        **base,
        "signer": subject.get("name"),
        "signer_tax_code": subject.get("tax_code"),
        "certificate_serial": signature.certificate.get("serial"),
        "issuer": signature.certificate.get("issuer"),
        "signed_at": signature.signed_at,
    }
    if document_hash(quotation_document(quotation)) != signature.document_hash:
        return {**signed, "state": "INVALID", "reason": "Nội dung báo giá đã bị thay đổi sau khi ký."}
    ok, reason = verify_signature(signature.document_hash, signature.signature, signature.certificate, signature.signed_at)
    if ok is None:
        return {**signed, "state": "UNVERIFIABLE", "reason": reason}
    return {**signed, "state": "VALID" if ok else "INVALID", **({"reason": reason} if not ok else {})}
