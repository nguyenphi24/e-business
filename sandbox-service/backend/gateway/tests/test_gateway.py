from decimal import Decimal

from django.test import TestCase, override_settings

from core.testing import API_HEADERS, TEST_SETTINGS, capture_callbacks
from gateway.models import Transaction

PAYLOAD = {
	"merchant_ref": "PAY-001",
	"amount": "1500000.00",
	"description": "Thanh toán INV-2026-0001",
	"return_url": "http://shop.test/invoices",
	"ipn_url": "http://merchant.test/api/v1/webhooks/payment",
}


@override_settings(**TEST_SETTINGS)
class GatewayTests(TestCase):
	def create(self, **overrides):
		return self.client.post("/api/v1/gateway/transactions", {**PAYLOAD, **overrides}, content_type="application/json", **API_HEADERS)

	def test_api_key_required(self):
		response = self.client.post("/api/v1/gateway/transactions", PAYLOAD, content_type="application/json")
		self.assertEqual(response.status_code, 403)

	def test_create_is_idempotent_on_merchant_ref(self):
		first = self.create()
		self.assertEqual(first.status_code, 201)
		body = first.json()
		self.assertTrue(body["success"])
		self.assertTrue(body["data"]["checkout_url"].startswith("http://sandbox.test/gateway/checkout/"))
		second = self.create()
		self.assertEqual(second.status_code, 200)
		self.assertEqual(second.json()["data"]["transaction_id"], body["data"]["transaction_id"])

	def test_rejects_callback_and_return_outside_allowlist(self):
		self.assertEqual(self.create(merchant_ref="PAY-002", ipn_url="http://evil.test/hook").status_code, 400)
		self.assertEqual(self.create(merchant_ref="PAY-003", return_url="http://evil.test/").status_code, 400)

	def test_checkout_success_sends_signed_ipn_and_redirects(self):
		transaction_id = self.create().json()["data"]["transaction_id"]
		page = self.client.get(f"/gateway/checkout/{transaction_id}/")
		self.assertContains(page, "1.500.000")
		with capture_callbacks() as sent:
			response = self.client.post(f"/gateway/checkout/{transaction_id}/", {"action": "pay", "bank": "VCB"})
		self.assertEqual(response.status_code, 302)
		self.assertIn("payment_ref=PAY-001", response["Location"])
		self.assertIn("status=SUCCEEDED", response["Location"])
		self.assertEqual(Transaction.objects.get(pk=transaction_id).status, Transaction.Status.SUCCEEDED)
		self.assertEqual(len(sent), 1)
		self.assertTrue(sent[0]["signature_ok"])
		self.assertEqual(sent[0]["payload"]["external_ref"], "PAY-001")
		self.assertEqual(sent[0]["payload"]["status"], "SUCCEEDED")
		self.assertEqual(Decimal(sent[0]["payload"]["amount"]), Decimal("1500000"))

		with capture_callbacks() as again:
			self.client.post(f"/gateway/checkout/{transaction_id}/", {"action": "fail"})
		self.assertEqual(again, [])
		self.assertEqual(Transaction.objects.get(pk=transaction_id).status, Transaction.Status.SUCCEEDED)

	def test_cancel_reports_failed_and_resend_keeps_event_id(self):
		transaction_id = self.create().json()["data"]["transaction_id"]
		with capture_callbacks() as sent:
			self.client.post(f"/gateway/checkout/{transaction_id}/", {"action": "cancel"})
			resend = self.client.post(f"/api/v1/gateway/transactions/{transaction_id}/resend-ipn", **API_HEADERS)
		self.assertEqual(resend.status_code, 200)
		self.assertEqual(sent[0]["payload"]["status"], "FAILED")
		self.assertEqual(sent[0]["payload"]["event_id"], sent[1]["payload"]["event_id"])
