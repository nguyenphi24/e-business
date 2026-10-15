from django.test import TestCase, override_settings

from core.testing import API_HEADERS, TEST_SETTINGS, capture_callbacks
from einvoice.models import EInvoice


def payload(**overrides):
	data = {
		"external_ref": "INV-2026-0001",
		"seller": {"tax_code": "0200000002", "name": "TechVision"},
		"buyer": {"tax_code": "0100000001", "name": "VNPT Media"},
		"issue_date": "2026-10-14",
		"lines": [
			{"name": "Màn hình", "unit": "cái", "quantity": "10", "unit_price": "4000000.00", "amount": "40000000.00"},
			{"name": "Cáp HDMI", "unit": "sợi", "quantity": "20", "unit_price": "120000.00", "amount": "2400000.00"},
		],
		"subtotal": "42400000.00",
		"vat_rate": "10",
		"vat_amount": "4240000.00",
		"total": "46640000.00",
		"callback_url": "http://merchant.test/api/v1/webhooks/einvoice",
	}
	data.update(overrides)
	return data


@override_settings(**TEST_SETTINGS)
class EInvoiceTests(TestCase):
	def create(self, **overrides):
		return self.client.post("/api/v1/einvoices", payload(**overrides), content_type="application/json", **API_HEADERS)

	def test_issue_assigns_number_and_tax_code_then_calls_back(self):
		with capture_callbacks() as sent:
			response = self.create()
		self.assertEqual(response.status_code, 201)
		data = response.json()["data"]
		self.assertEqual(data["symbol"], "SBX26")
		self.assertEqual(data["number"], 1)
		self.assertEqual(data["status"], "ISSUED")
		self.assertTrue(data["tax_code"].startswith("SBX26-"))
		self.assertEqual(len(sent), 1)
		self.assertTrue(sent[0]["signature_ok"])
		self.assertEqual(sent[0]["payload"]["external_ref"], "INV-2026-0001")
		self.assertEqual(sent[0]["payload"]["status"], "ISSUED")

		second = self.create(external_ref="INV-2026-0002")
		self.assertEqual(second.json()["data"]["number"], 2)
		again = self.create()
		self.assertEqual(again.status_code, 200)
		self.assertEqual(EInvoice.objects.count(), 2)

	def test_rejects_wrong_arithmetic_and_vat_rate(self):
		self.assertEqual(self.create(vat_amount="1.00").status_code, 400)
		self.assertEqual(self.create(external_ref="X2", total="1.00").status_code, 400)
		self.assertEqual(self.create(external_ref="X3", vat_rate="7").status_code, 400)
		self.assertEqual(EInvoice.objects.count(), 0)

	@override_settings(EINVOICE_TAX_DELAY_SECONDS=3600)
	def test_tax_code_waits_for_tax_authority(self):
		with capture_callbacks() as sent, self.captureOnCommitCallbacks(execute=False):
			data = self.create().json()["data"]
		self.assertEqual(data["status"], "PENDING_TAX_CODE")
		self.assertEqual(sent, [])

	def test_lookup_page_and_xml(self):
		with capture_callbacks():
			code = self.create().json()["data"]["lookup_code"]
		page = self.client.get(f"/einvoice/lookup/?code={code}")
		self.assertContains(page, "46.640.000")
		self.assertContains(page, "GIẢ LẬP")
		self.assertContains(page, "<td class=\"num\">10</td>")
		self.assertContains(page, "<td class=\"num\">20</td>")
		xml = self.client.get(f"/einvoice/{code}/xml/")
		self.assertEqual(xml.status_code, 200)
		self.assertIn(b"<HoaDonGiaLap", xml.content)
		self.assertIn(b"<TienThueGTGT>4240000.00</TienThueGTGT>", xml.content)
		self.assertContains(self.client.get("/einvoice/lookup/?code=NOPE"), "Không tìm thấy")
