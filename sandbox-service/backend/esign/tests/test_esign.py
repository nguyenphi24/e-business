import base64
import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.test import TestCase, override_settings

from core.callbacks import canonical_json
from core.testing import API_HEADERS, TEST_SETTINGS, capture_callbacks
from esign.models import SignRequest

DOCUMENT_HASH = hashlib.sha256(b"quotation RFQ-2026-0001 rev 1").hexdigest()


@override_settings(**TEST_SETTINGS)
class ESignTests(TestCase):
	def create(self, external_ref="QS-1"):
		return self.client.post("/api/v1/esign/requests", {
			"external_ref": external_ref,
			"signer": {"tax_code": "0200000002", "name": "TechVision"},
			"document_hash": DOCUMENT_HASH,
			"document_label": "Báo giá RFQ-2026-0001 (lần 1)",
			"callback_url": "http://merchant.test/api/v1/webhooks/esign",
		}, content_type="application/json", **API_HEADERS)

	def test_rejects_non_hex_hash(self):
		response = self.client.post("/api/v1/esign/requests", {
			"external_ref": "QS-X", "signer": {"tax_code": "1", "name": "A"}, "document_hash": "z" * 64,
			"document_label": "x", "callback_url": "http://merchant.test/x",
		}, content_type="application/json", **API_HEADERS)
		self.assertEqual(response.status_code, 400)

	def test_sign_with_otp_produces_verifiable_signature(self):
		data = self.create().json()["data"]
		self.assertTrue(data["sign_url"].startswith("http://sandbox.test/esign/sign/"))
		request = SignRequest.objects.get(pk=data["request_id"])
		self.assertContains(self.client.get(f"/esign/sign/{request.id}/"), request.otp)
		with capture_callbacks() as sent:
			self.client.post(f"/esign/sign/{request.id}/", {"action": "sign", "otp": request.otp})
		event = sent[0]["payload"]
		self.assertTrue(sent[0]["signature_ok"])
		self.assertEqual(event["status"], "SIGNED")

		ca_key = self.client.get("/api/v1/esign/ca").json()["data"]["public_key"]
		certificate = dict(event["certificate"])
		ca_signature = certificate.pop("ca_signature")
		Ed25519PublicKey.from_public_bytes(base64.b64decode(ca_key)).verify(base64.b64decode(ca_signature), canonical_json(certificate))
		signer_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(certificate["public_key"]))
		signer_key.verify(base64.b64decode(event["signature"]), bytes.fromhex(DOCUMENT_HASH))
		self.assertEqual(certificate["subject"]["tax_code"], "0200000002")

	def test_wrong_otp_three_times_locks_request(self):
		request_id = self.create().json()["data"]["request_id"]
		with capture_callbacks() as sent:
			for _ in range(2):
				page = self.client.post(f"/esign/sign/{request_id}/", {"action": "sign", "otp": "000000x"})
				self.assertContains(page, "OTP không đúng")
			self.client.post(f"/esign/sign/{request_id}/", {"action": "sign", "otp": "000000x"})
		self.assertEqual(SignRequest.objects.get(pk=request_id).status, SignRequest.Status.LOCKED)
		self.assertEqual([item["payload"]["status"] for item in sent], ["LOCKED"])

	def test_reject_and_same_certificate_reused(self):
		request_id = self.create().json()["data"]["request_id"]
		with capture_callbacks() as sent:
			self.client.post(f"/esign/sign/{request_id}/", {"action": "reject"})
		self.assertEqual(sent[0]["payload"]["status"], "REJECTED")
		self.assertEqual(self.create().status_code, 200)
