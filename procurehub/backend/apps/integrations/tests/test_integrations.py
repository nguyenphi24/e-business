import base64
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.billing.models import Invoice, Payment
from apps.integrations.client import IntegrationError, SandboxClient
from apps.integrations.models import TrustAnchor
from apps.integrations.security import canonical_json, sign
from apps.notifications.models import Notification
from apps.procurement.models import QuotationLine, QuotationSignature
from apps.procurement.tests.flow import ProcurementFlowMixin

SANDBOX = {"SANDBOX_BASE_URL": "http://sandbox.test", "SANDBOX_API_KEY": "key", "SANDBOX_WEBHOOK_SECRET": "test-webhook-secret"}


def raw_public(key):
    return base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


class WebhookMixin:
    def post_webhook(self, path, event):
        raw = canonical_json(event)
        self.client.force_authenticate(None)
        return self.client.post(path, data=raw, content_type="application/json", HTTP_X_SANDBOX_SIGNATURE=sign(raw))


@override_settings(**SANDBOX)
class PaymentGatewayTests(WebhookMixin, ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()
        self.as_user(self.tech_sales)
        po = self.delivered_po()
        self.as_user(self.tech_sales)
        with mock.patch.object(SandboxClient, "create_einvoice", side_effect=IntegrationError("offline")):
            self.invoice = self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/invoice", {}, format="json"), status.HTTP_201_CREATED)

    def create_payment(self, amount):
        self.as_user(self.finance)
        return self.client.post(f"/api/v1/invoices/{self.invoice['id']}/payments", {"amount": amount}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def test_payment_goes_through_gateway_and_ipn(self):
        with mock.patch.object(SandboxClient, "create_payment", return_value={"transaction_id": "tx-1", "checkout_url": "http://sandbox.test/gateway/checkout/tx-1/"}) as create:
            body = self.ok(self.create_payment("1000"), status.HTTP_201_CREATED)
        payment = body["payment"]
        self.assertEqual(payment["provider"], "SANDBOX_GW")
        self.assertEqual(payment["checkout_url"], "http://sandbox.test/gateway/checkout/tx-1/")
        self.assertEqual(create.call_args.kwargs["ipn_url"], "http://127.0.0.1:48000/api/v1/webhooks/payment")
        self.assertIn(f"/invoices?payment={payment['id']}", create.call_args.kwargs["return_url"])

        simulate = self.client.post(f"/api/v1/payments/{payment['id']}/simulate", {"outcome": "SUCCEEDED"}, format="json")
        self.assertIn(simulate.status_code, {403, 409})

        event = {"event_id": "evt-1", "external_ref": payment["external_ref"], "status": "SUCCEEDED", "amount": "999.00"}
        self.assertEqual(self.post_webhook("/api/v1/webhooks/payment", event).data["code"], "amount_mismatch")
        self.assertEqual(Payment.objects.get(pk=payment["id"]).status, Payment.Status.PENDING)

        event.update(event_id="evt-2", amount="1000.00")
        self.assertEqual(self.post_webhook("/api/v1/webhooks/payment", event).status_code, 200)
        invoice = Invoice.objects.get(pk=self.invoice["id"])
        self.assertEqual(invoice.status, Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(invoice.paid_amount, Decimal("1000"))

    def test_gateway_unreachable_marks_payment_failed_and_frees_balance(self):
        with mock.patch.object(SandboxClient, "create_payment", side_effect=IntegrationError("down")):
            body = self.ok(self.create_payment(self.invoice["total"]), status.HTTP_201_CREATED)
        self.assertEqual(body["payment"]["status"], "FAILED")
        with mock.patch.object(SandboxClient, "create_payment", return_value={"transaction_id": "tx-2", "checkout_url": "http://sandbox.test/x"}):
            self.ok(self.create_payment(self.invoice["total"]), status.HTTP_201_CREATED)


def einvoice_data(status_value, **extra):
    return {
        "einvoice_id": "e-1", "external_ref": "INV-X", "symbol": "SBX26", "number": 7, "lookup_code": "ABCDE12345",
        "status": status_value, "tax_code": "SBX26-0011223344556677" if status_value == "ISSUED" else "",
        "lookup_url": "http://sandbox.test/einvoice/lookup/?code=ABCDE12345", "xml_url": "http://sandbox.test/einvoice/ABCDE12345/xml/",
        **extra,
    }


@override_settings(**SANDBOX)
class EInvoiceTests(WebhookMixin, ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()
        self.po = self.delivered_po()

    def issue(self, **patch_kwargs):
        self.as_user(self.tech_sales)
        with mock.patch.object(SandboxClient, "create_einvoice", **patch_kwargs) as create:
            invoice = self.ok(self.client.post(f"/api/v1/purchase-orders/{self.po['id']}/invoice", {}, format="json"), status.HTTP_201_CREATED)
        return invoice, create

    def test_invoice_is_submitted_with_vat_and_issued_by_callback(self):
        invoice, create = self.issue(return_value=einvoice_data("PENDING_TAX_CODE"))
        payload = create.call_args.args[0]
        self.assertEqual(payload["external_ref"], invoice["number"])
        self.assertEqual(payload["seller"]["tax_code"], self.tech.tax_code)
        self.assertEqual(Decimal(payload["subtotal"]), sum(Decimal(line["amount"]) for line in payload["lines"]))
        self.assertEqual(Decimal(payload["vat_amount"]), Decimal(payload["subtotal"]) / 10)
        self.assertEqual(Decimal(payload["total"]), Decimal(invoice["total"]))
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).einvoice_status, Invoice.EInvoiceStatus.PENDING_TAX_CODE)

        event = {"event_id": "evt-e1", **einvoice_data("ISSUED", external_ref=invoice["number"])}
        self.assertFalse(self.post_webhook("/api/v1/webhooks/einvoice", event).data["ignored"])
        stored = Invoice.objects.get(pk=invoice["id"])
        self.assertEqual(stored.einvoice_status, Invoice.EInvoiceStatus.ISSUED)
        self.assertEqual(stored.einvoice_tax_code, "SBX26-0011223344556677")
        self.assertTrue(Notification.objects.filter(recipient=self.finance, event_type="EINVOICE_ISSUED").exists())
        self.assertTrue(self.post_webhook("/api/v1/webhooks/einvoice", event).data["ignored"])

        self.as_user(self.tech_sales)
        cancel = self.client.post(f"/api/v1/invoices/{invoice['id']}/cancel", {}, format="json")
        self.assertEqual(cancel.status_code, status.HTTP_409_CONFLICT)

    def test_provider_failure_can_be_retried(self):
        invoice, _ = self.issue(side_effect=IntegrationError("offline"))
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).einvoice_status, Invoice.EInvoiceStatus.FAILED)
        self.as_user(self.tech_sales)
        with mock.patch.object(SandboxClient, "create_einvoice", return_value=einvoice_data("ISSUED")):
            retried = self.ok(self.client.post(f"/api/v1/invoices/{invoice['id']}/einvoice", {}, format="json"))
        self.assertEqual(retried["einvoice"]["status"], "ISSUED")
        self.as_user(self.finance)
        self.assertEqual(self.client.post(f"/api/v1/invoices/{invoice['id']}/einvoice", {}, format="json").status_code, status.HTTP_403_FORBIDDEN)

    def test_bad_signature_rejected(self):
        self.client.force_authenticate(None)
        response = self.client.post("/api/v1/webhooks/einvoice", data=b"{}", content_type="application/json", HTTP_X_SANDBOX_SIGNATURE="bad")
        self.assertEqual(response.status_code, 401)


@override_settings(**SANDBOX)
class QuotationSignatureTests(WebhookMixin, ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()
        self.ca_key = Ed25519PrivateKey.generate()
        self.signer_key = Ed25519PrivateKey.generate()
        TrustAnchor.objects.create(name="sandbox-ca", issuer="Test CA", public_key=raw_public(self.ca_key))
        self.rfq, self.tech_quote, _ = self.closed_rfq_with_quotes()

    def certificate(self, tax_code=None, ca_key=None):
        now = timezone.now()
        body = {
            "serial": "ABC", "issuer": "Test CA", "subject": {"tax_code": tax_code or self.tech.tax_code, "name": "Tech Co"},
            "algorithm": "Ed25519", "public_key": raw_public(self.signer_key),
            "valid_from": (now - timedelta(days=1)).isoformat(), "valid_to": (now + timedelta(days=365)).isoformat(),
        }
        body["ca_signature"] = base64.b64encode((ca_key or self.ca_key).sign(canonical_json(body))).decode()
        return body

    def request_sign(self):
        self.as_user(self.tech_sales)
        with mock.patch.object(SandboxClient, "create_sign_request", return_value={"request_id": "r-1", "sign_url": "http://sandbox.test/esign/sign/r-1/"}) as create:
            response = self.ok(self.client.post(f"/api/v1/quotations/{self.tech_quote['id']}/sign", {}, format="json"))
        return response, create

    def signed_event(self, signature_id, document_hash, **certificate_kwargs):
        return {
            "event_id": f"evt-{uuid.uuid4().hex}", "external_ref": signature_id, "status": "SIGNED", "document_hash": document_hash,
            "signature": base64.b64encode(self.signer_key.sign(bytes.fromhex(document_hash))).decode(),
            "signed_at": timezone.now().isoformat(), "certificate": self.certificate(**certificate_kwargs),
        }

    def comparison_signature(self):
        self.as_user(self.buyer)
        comparison = self.ok(self.client.get(f"/api/v1/rfqs/{self.rfq['id']}/comparison"))
        return next(item for item in comparison["quotations"] if item["id"] == self.tech_quote["id"])["signature"]

    def test_valid_signature_then_tampering_is_detected(self):
        response, create = self.request_sign()
        self.assertEqual(response["status"], "PENDING")
        self.assertEqual(response["sign_url"], "http://sandbox.test/esign/sign/r-1/")
        document_hash = create.call_args.kwargs["document_hash"]
        self.assertEqual(self.comparison_signature()["state"], "PENDING")
        self.assertNotIn("sign_url", self.comparison_signature())  # bên mua không thấy link ký

        result = self.post_webhook("/api/v1/webhooks/esign", self.signed_event(response["id"], document_hash))
        self.assertEqual(result.data["status"], "SIGNED")
        signature = self.comparison_signature()
        self.assertEqual(signature["state"], "VALID")
        self.assertEqual(signature["signer_tax_code"], self.tech.tax_code)
        self.assertTrue(Notification.objects.filter(recipient=self.buyer, event_type="QUOTATION_SIGNED").exists())

        QuotationLine.objects.filter(quotation_id=self.tech_quote["id"]).update(unit_price=Decimal("1"))
        tampered = self.comparison_signature()
        self.assertEqual(tampered["state"], "INVALID")
        self.assertIn("thay đổi", tampered["reason"])

    def test_signature_from_wrong_ca_or_wrong_supplier_is_refused(self):
        response, create = self.request_sign()
        document_hash = create.call_args.kwargs["document_hash"]
        self.post_webhook("/api/v1/webhooks/esign", self.signed_event(response["id"], document_hash, ca_key=Ed25519PrivateKey.generate()))
        self.assertEqual(QuotationSignature.objects.get(pk=response["id"]).status, QuotationSignature.Status.FAILED)

        response, create = self.request_sign()
        self.post_webhook("/api/v1/webhooks/esign", self.signed_event(response["id"], create.call_args.kwargs["document_hash"], tax_code=self.digital.tax_code))
        stored = QuotationSignature.objects.get(pk=response["id"])
        self.assertEqual(stored.status, QuotationSignature.Status.FAILED)
        self.assertIn("không thuộc", stored.failure_reason)

    def test_only_owner_can_sign_and_requires_integration(self):
        self.as_user(self.digital_sales)
        self.assertEqual(self.client.post(f"/api/v1/quotations/{self.tech_quote['id']}/sign", {}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        with override_settings(SANDBOX_BASE_URL=""):
            self.as_user(self.tech_sales)
            self.assertEqual(self.client.post(f"/api/v1/quotations/{self.tech_quote['id']}/sign", {}, format="json").status_code, status.HTTP_409_CONFLICT)
