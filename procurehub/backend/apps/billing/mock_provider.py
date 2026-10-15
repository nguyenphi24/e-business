"""Cổng thanh toán giả lập cho demo (Sandbox). Không chuyển tiền thật, không nhận dữ liệu thẻ."""
import uuid

from django.utils import timezone

from apps.billing.services import process_payment_event
from apps.integrations.security import canonical_json, sign


def build_event(payment, outcome):
    return {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "external_ref": payment.external_ref,
        "status": outcome,
        "amount": str(payment.amount),
        "occurred_at": timezone.now().isoformat(),
    }


def signed_body(event):
    """Body và chữ ký như cổng thanh toán gửi tới POST /api/v1/webhooks/payment."""
    raw = canonical_json(event)
    return raw, sign(raw)


def simulate(payment, outcome):
    return process_payment_event(build_event(payment, outcome), source="sandbox_simulate")
