"""Callback từ sandbox-service. Không dùng JWT: xác thực bằng HMAC-SHA256 trên raw body."""
import json

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.services import apply_einvoice_event, process_payment_event
from apps.integrations.security import SIGNATURE_HEADER, verify
from apps.procurement.esign import apply_sign_event
from common.exceptions import DomainError


class SignedWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def handle_event(self, event):
        raise NotImplementedError

    def post(self, request):
        raw_body = request.body  # đọc raw trước khi DRF parse để tính HMAC đúng từng byte
        if not verify(raw_body, request.headers.get(SIGNATURE_HEADER, "")):
            raise DomainError("invalid_signature", "Webhook signature is invalid.", status_code=401)
        try:
            event = json.loads(raw_body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise DomainError("validation_error", "Body must be valid JSON.", status_code=422) from exc
        if not isinstance(event, dict):
            raise DomainError("validation_error", "Body must be a JSON object.", status_code=422)
        return Response(self.handle_event(event))


class PaymentWebhookView(SignedWebhookView):
    def handle_event(self, event):
        return process_payment_event(event, source="payment_gateway")


class EInvoiceWebhookView(SignedWebhookView):
    def handle_event(self, event):
        return apply_einvoice_event(event)


class ESignWebhookView(SignedWebhookView):
    def handle_event(self, event):
        return apply_sign_event(event)
