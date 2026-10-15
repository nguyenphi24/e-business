"""Chuẩn bị dữ liệu giả lập cho buổi demo.

- Luôn bảo đảm có CA và chứng thư ký số cho các nhà cung cấp trong dữ liệu mẫu ProcureHub.
- `--reset`: xóa giao dịch thanh toán, hóa đơn điện tử, yêu cầu ký, log callback (giữ CA để khóa CA mà
  ProcureHub đã ghim vẫn hợp lệ; số hóa đơn đánh lại từ 1).
- `--reset-ca`: tạo lại cả CA và chứng thư — sau đó phải chạy `seed_demo --reset` bên ProcureHub (xóa khóa
  CA đã ghim), nếu không mọi chữ ký mới sẽ bị coi là "không do CA tin cậy cấp".
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import CallbackLog
from einvoice.models import EInvoice
from esign.crypto import certificate_for, get_ca
from esign.models import CertificateAuthority, SignerCertificate, SignRequest
from gateway.models import Transaction

# Phải trùng MST/tên công ty trong procurehub/backend/apps/identity/management/commands/seed_demo.py
DEMO_SIGNERS = [
	("0200000002", "TechVision"),
	("0300000003", "Digital Supply"),
]


class Command(BaseCommand):
	help = "Chuẩn bị dữ liệu giả lập (CA, chứng thư ký số); --reset để xóa giao dịch cũ"

	def add_arguments(self, parser):
		parser.add_argument("--reset", action="store_true", help="Xóa giao dịch, hóa đơn, yêu cầu ký, log callback (giữ CA)")
		parser.add_argument("--reset-ca", action="store_true", help="Tạo lại CA và chứng thư (kèm --reset)")

	@transaction.atomic
	def handle(self, *args, **options):
		if options["reset"] or options["reset_ca"]:
			counts = {
				"giao dịch thanh toán": Transaction.objects.all().delete()[0],
				"hóa đơn điện tử": EInvoice.objects.all().delete()[0],
				"yêu cầu ký": SignRequest.objects.all().delete()[0],
				"log callback": CallbackLog.objects.all().delete()[0],
			}
			self.stdout.write("Đã xóa: " + ", ".join(f"{count} {name}" for name, count in counts.items()))
		if options["reset_ca"]:
			SignerCertificate.objects.all().delete()
			CertificateAuthority.objects.all().delete()
			self.stdout.write(self.style.WARNING(
				"Đã tạo lại CA — chạy `manage.py seed_demo --reset` bên ProcureHub để bỏ khóa CA cũ đã ghim."
			))

		ca = get_ca()
		self.stdout.write(self.style.SUCCESS(f"CA: {ca.name}"))
		self.stdout.write(f"  khóa công khai: {ca.public_key}")
		for tax_code, name in DEMO_SIGNERS:
			certificate = certificate_for(tax_code, name)
			self.stdout.write(f"  chứng thư {certificate.serial}: {name} (MST {tax_code}), hiệu lực đến {certificate.certificate['valid_to'][:10]}")
		self.stdout.write(self.style.SUCCESS(
			f"Sẵn sàng: {Transaction.objects.count()} giao dịch, {EInvoice.objects.count()} hóa đơn, {SignRequest.objects.count()} yêu cầu ký"
		))
