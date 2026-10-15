import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.billing import mock_provider
from apps.billing.models import Invoice, Payment, PaymentEvent
from apps.notifications.models import Notification
from apps.procurement.tests.flow import ProcurementFlowMixin

WEBHOOK = "/api/v1/webhooks/payment"


@override_settings(PAYMENT_SANDBOX_ENABLED=True)
class InvoiceAndPaymentTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()

    def issue_invoice(self, po):
        self.as_user(self.tech_sales)
        return self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/invoice", {}, format="json"), status.HTTP_201_CREATED)

    def create_payment(self, invoice_id, amount, key=None):
        self.as_user(self.finance)
        return self.client.post(
            f"/api/v1/invoices/{invoice_id}/payments", {"amount": amount}, format="json",
            HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
        )

    def simulate(self, payment_id, outcome="SUCCEEDED"):
        self.as_user(self.finance)
        return self.client.post(f"/api/v1/payments/{payment_id}/simulate", {"outcome": outcome}, format="json")

    def test_invoice_requires_delivered_po(self):
        po = self.issued_po()
        self.as_user(self.tech_sales)
        response = self.client.post(f"/api/v1/purchase-orders/{po['id']}/invoice", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_invoice_uses_po_terms_and_is_unique(self):
        po = self.delivered_po()
        self.assertEqual(po["payment_term_days"], 30)
        self.assertIsNotNone(po["delivered_at"])
        invoice = self.issue_invoice(po)
        self.assertEqual(invoice["status"], "ISSUED")
        self.assertEqual(Decimal(invoice["subtotal"]), Decimal(po["total"]))
        self.assertEqual(Decimal(invoice["vat_rate"]), Decimal("10"))
        self.assertEqual(Decimal(invoice["vat_amount"]), Decimal(po["total"]) / 10)
        self.assertEqual(Decimal(invoice["total"]), Decimal(po["total"]) * Decimal("1.1"))
        self.assertEqual(invoice["einvoice"]["status"], "NOT_SENT")
        self.assertEqual(invoice["due_date"], str(timezone.now().date() + timedelta(days=30)))
        self.assertTrue(Notification.objects.filter(recipient=self.finance, event_type="INVOICE_ISSUED").exists())
        again = self.client.post(f"/api/v1/purchase-orders/{po['id']}/invoice", {}, format="json")
        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)

    def test_other_tenant_cannot_see_invoice(self):
        invoice = self.issue_invoice(self.delivered_po())
        self.as_user(self.other_finance)
        self.assertEqual(self.client.get(f"/api/v1/invoices/{invoice['id']}").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.create_payment_as(self.other_finance, invoice["id"], "1").status_code, status.HTTP_404_NOT_FOUND)
        self.as_user(self.digital_sales)
        self.assertEqual(self.client.get(f"/api/v1/invoices/{invoice['id']}").status_code, status.HTTP_404_NOT_FOUND)

    def create_payment_as(self, user, invoice_id, amount):
        self.as_user(user)
        return self.client.post(
            f"/api/v1/invoices/{invoice_id}/payments", {"amount": amount}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )

    def test_partial_then_full_payment(self):
        invoice = self.issue_invoice(self.delivered_po())
        total = Decimal(invoice["total"])
        part = (total * Decimal("0.3")).quantize(Decimal("0.01"))

        created = self.ok(self.create_payment(invoice["id"], str(part)), status.HTTP_201_CREATED)
        self.assertEqual(created["payment"]["status"], "PENDING")
        result = self.ok(self.simulate(created["payment"]["id"]))
        self.assertEqual(result["invoice"]["status"], "PARTIALLY_PAID")
        self.assertEqual(Decimal(result["invoice"]["balance"]), total - part)
        self.assertTrue(Notification.objects.filter(recipient=self.tech_sales, event_type="PAYMENT_SUCCEEDED").exists())

        rest = self.ok(self.create_payment(invoice["id"], str(total - part)), status.HTTP_201_CREATED)
        result = self.ok(self.simulate(rest["payment"]["id"]))
        self.assertEqual(result["invoice"]["status"], "PAID")
        self.assertEqual(Decimal(result["invoice"]["balance"]), Decimal("0"))

    def test_failed_payment_keeps_balance(self):
        invoice = self.issue_invoice(self.delivered_po())
        created = self.ok(self.create_payment(invoice["id"], "1000"), status.HTTP_201_CREATED)
        result = self.ok(self.simulate(created["payment"]["id"], "FAILED"))
        self.assertEqual(result["invoice"]["status"], "ISSUED")
        self.assertEqual(Decimal(result["invoice"]["paid_amount"]), Decimal("0"))

    def test_payment_validation(self):
        invoice = self.issue_invoice(self.delivered_po())
        total = Decimal(invoice["total"])
        too_much = self.create_payment(invoice["id"], str(total + 1))
        self.assertEqual(too_much.status_code, 422)
        self.assertEqual(too_much.data["code"], "payment_exceeds_balance")

        self.ok(self.create_payment(invoice["id"], str(total)), status.HTTP_201_CREATED)
        pending_blocks = self.create_payment(invoice["id"], "1")
        self.assertEqual(pending_blocks.data["code"], "payment_exceeds_balance")

        self.as_user(self.finance)
        missing_key = self.client.post(f"/api/v1/invoices/{invoice['id']}/payments", {"amount": "1"}, format="json")
        self.assertEqual(missing_key.status_code, 422)

        self.as_user(self.buyer)
        forbidden = self.client.post(
            f"/api/v1/invoices/{invoice['id']}/payments", {"amount": "1"}, format="json", HTTP_IDEMPOTENCY_KEY="k"
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_payment_creation_is_idempotent(self):
        invoice = self.issue_invoice(self.delivered_po())
        first = self.create_payment(invoice["id"], "1000", key="same-key")
        second = self.create_payment(invoice["id"], "1000", key="same-key")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["payment"]["id"], second.data["payment"]["id"])
        self.assertEqual(Payment.objects.count(), 1)

    def test_webhook_rejects_bad_signature_and_ignores_duplicates(self):
        invoice = self.issue_invoice(self.delivered_po())
        payment_id = self.ok(self.create_payment(invoice["id"], "1000"), status.HTTP_201_CREATED)["payment"]["id"]
        payment = Payment.objects.get(pk=payment_id)
        event = mock_provider.build_event(payment, "SUCCEEDED")
        raw, signature = mock_provider.signed_body(event)
        self.client.force_authenticate(None)

        bad = self.client.post(WEBHOOK, data=raw, content_type="application/json", HTTP_X_SANDBOX_SIGNATURE="0" * 64)
        self.assertEqual(bad.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(bad.data["code"], "invalid_signature")

        first = self.client.post(WEBHOOK, data=raw, content_type="application/json", HTTP_X_SANDBOX_SIGNATURE=signature)
        second = self.client.post(WEBHOOK, data=raw, content_type="application/json", HTTP_X_SANDBOX_SIGNATURE=signature)
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.data["duplicate"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).paid_amount, Decimal("1000"))
        self.assertEqual(PaymentEvent.objects.get(event_id=event["event_id"]).duplicate_count, 1)

        # Sự kiện mới cho payment đã ở trạng thái cuối không cộng thêm tiền
        late = mock_provider.build_event(payment, "SUCCEEDED")
        raw_late, signature_late = mock_provider.signed_body(late)
        response = self.client.post(WEBHOOK, data=raw_late, content_type="application/json", HTTP_X_SANDBOX_SIGNATURE=signature_late)
        self.assertTrue(response.data["ignored"])
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).paid_amount, Decimal("1000"))

    @override_settings(PAYMENT_SANDBOX_ENABLED=False)
    def test_simulate_requires_sandbox_flag(self):
        invoice = self.issue_invoice(self.delivered_po())
        payment_id = self.ok(self.create_payment(invoice["id"], "1000"), status.HTTP_201_CREATED)["payment"]["id"]
        response = self.simulate(payment_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "sandbox_disabled")

    def test_supplier_can_cancel_unpaid_invoice_only(self):
        po = self.delivered_po()
        invoice = self.issue_invoice(po)
        self.ok(self.client.post(f"/api/v1/invoices/{invoice['id']}/cancel", {}, format="json"))
        replacement = self.issue_invoice(po)
        self.ok(self.create_payment(replacement["id"], "1000"), status.HTTP_201_CREATED)
        self.as_user(self.tech_sales)
        response = self.client.post(f"/api/v1/invoices/{replacement['id']}/cancel", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class EvaluationAndDashboardTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()

    def test_evaluation_rules_and_rating_summary(self):
        po = self.delivered_po()
        early = self.client.post(f"/api/v1/purchase-orders/{po['id']}/evaluation", {"quality_score": 5, "delivery_score": 4}, format="json")
        self.assertEqual(early.status_code, status.HTTP_409_CONFLICT)
        self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/complete", {}, format="json"))

        invalid = self.client.post(f"/api/v1/purchase-orders/{po['id']}/evaluation", {"quality_score": 6, "delivery_score": 4}, format="json")
        self.assertEqual(invalid.status_code, 422)
        evaluated = self.ok(self.client.post(
            f"/api/v1/purchase-orders/{po['id']}/evaluation", {"quality_score": 5, "delivery_score": 4, "comment": "Tốt"}, format="json"
        ), status.HTTP_201_CREATED)
        self.assertEqual(evaluated["evaluation"]["quality_score"], 5)
        twice = self.client.post(f"/api/v1/purchase-orders/{po['id']}/evaluation", {"quality_score": 5, "delivery_score": 4}, format="json")
        self.assertEqual(twice.status_code, status.HTTP_409_CONFLICT)
        self.as_user(self.tech_sales)
        self.assertIsNone(self.ok(self.client.get(f"/api/v1/purchase-orders/{po['id']}"))["evaluation"])
        self.as_user(self.buyer)

        suppliers = self.ok(self.client.get("/api/v1/suppliers"))["results"]
        tech = next(item for item in suppliers if item["supplier_company"]["id"] == str(self.tech.id))
        self.assertEqual(Decimal(tech["rating_average"]), Decimal("4.50"))
        self.assertEqual(tech["rating_count"], 1)

    def test_dashboard_reports_kpis_for_buyer_side_only(self):
        self.delivered_po(complete=True)
        self.as_user(self.manager)
        dashboard = self.ok(self.client.get("/api/v1/dashboard"))
        kpis = dashboard["kpis"]
        self.assertEqual(set(kpis), {
            "approval_lead_time_hours", "rfq_response_time_hours", "quote_participation_rate",
            "procurement_cycle_time_days", "on_time_delivery_rate", "estimated_savings",
        })
        self.assertEqual(kpis["quote_participation_rate"]["value"], 1.0)
        self.assertEqual(kpis["quote_participation_rate"]["n"], 2)
        self.assertEqual(kpis["on_time_delivery_rate"]["value"], 1.0)
        # Ngân sách 25.000.000 − PO 18.000.000
        self.assertEqual(Decimal(kpis["estimated_savings"]["value"]), Decimal("7000000.00"))
        self.assertEqual(kpis["approval_lead_time_hours"]["n"], 1)

        self.as_user(self.tech_sales)
        supplier_dashboard = self.ok(self.client.get("/api/v1/dashboard"))
        self.assertIsNone(supplier_dashboard["kpis"])
        self.assertIn("INVOICE_CREATE", [item["type"] for item in supplier_dashboard["pending_actions"]])
