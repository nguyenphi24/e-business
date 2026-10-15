from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from core.testing import TEST_SETTINGS
from esign.models import CertificateAuthority, SignerCertificate
from gateway.models import Transaction


@override_settings(**TEST_SETTINGS)
class SeedSandboxTests(TestCase):
	def run_seed(self, *args):
		out = StringIO()
		call_command("seed_sandbox", *args, stdout=out)
		return out.getvalue()

	def test_creates_ca_and_demo_certificates_idempotently(self):
		self.run_seed()
		ca_key = CertificateAuthority.objects.get().public_key
		self.assertEqual(set(SignerCertificate.objects.values_list("tax_code", flat=True)), {"0200000002", "0300000003"})
		self.run_seed()
		self.assertEqual(CertificateAuthority.objects.get().public_key, ca_key)
		self.assertEqual(SignerCertificate.objects.count(), 2)

	def test_reset_keeps_ca_but_reset_ca_rotates_it(self):
		self.run_seed()
		ca_key = CertificateAuthority.objects.get().public_key
		Transaction.objects.create(merchant_ref="PAY-X", amount=1, return_url="http://shop.test/", ipn_url="http://merchant.test/")
		self.run_seed("--reset")
		self.assertEqual(Transaction.objects.count(), 0)
		self.assertEqual(CertificateAuthority.objects.get().public_key, ca_key)
		output = self.run_seed("--reset-ca")
		self.assertNotEqual(CertificateAuthority.objects.get().public_key, ca_key)
		self.assertIn("seed_demo --reset", output)
