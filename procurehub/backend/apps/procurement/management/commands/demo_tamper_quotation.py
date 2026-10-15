"""CHỈ DÙNG KHI DEMO: sửa thẳng đơn giá một dòng báo giá trong DB (bỏ qua API và audit) để minh họa
chữ ký số phát hiện dữ liệu bị thay đổi sau khi ký. Chạy lại với giá cũ để khôi phục."""
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum

from apps.procurement.models import Quotation, QuotationLine


class Command(BaseCommand):
    help = "Demo: sửa đơn giá dòng đầu tiên của một báo giá trực tiếp trong DB"

    def add_arguments(self, parser):
        parser.add_argument("--rfq", required=True, help="Số RFQ, ví dụ RFQ-2026-0002")
        parser.add_argument("--supplier-tax-code", required=True, help="MST nhà cung cấp, ví dụ 0200000002")
        parser.add_argument("--unit-price", required=True, type=Decimal, help="Đơn giá mới cho dòng đầu tiên")

    @transaction.atomic
    def handle(self, *args, **options):
        quotation = Quotation.objects.filter(
            rfq__number=options["rfq"], supplier_company__tax_code=options["supplier_tax_code"]
        ).first()
        if quotation is None:
            raise CommandError("Không tìm thấy báo giá.")
        line = quotation.lines.order_by("rfq_line_id").first()
        old_price = line.unit_price
        new_total = (line.offered_quantity * options["unit_price"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        QuotationLine.objects.filter(pk=line.pk).update(unit_price=options["unit_price"], line_total=new_total)
        total = QuotationLine.objects.filter(quotation=quotation).aggregate(value=Sum("line_total"))["value"]
        Quotation.objects.filter(pk=quotation.pk).update(total=total)
        self.stdout.write(self.style.WARNING(
            f"Đã sửa đơn giá dòng {line.rfq_line_id} của báo giá {quotation.id}: {old_price} → {options['unit_price']}. "
            f"Khôi phục: --unit-price {old_price}"
        ))
