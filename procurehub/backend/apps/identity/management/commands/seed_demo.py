"""Nạp dữ liệu demo theo Decisions Addendum mục 4 và URD mục 13. Chạy lại được: `--reset` xóa rồi nạp lại."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.billing.models import Invoice, Payment, PaymentEvent
from apps.identity.models import Company, User, UserRole
from apps.notifications.models import Notification
from apps.integrations.models import TrustAnchor
from apps.procurement.models import (
    RFQ, QuotationSignature, DocumentSequence, IdempotencyKey, PurchaseRequest, PurchaseRequestLine, Quotation,
    QuotationLine, QuotationRevision, RFQInvitation, RFQLine, SupplierSelection,
)
from apps.purchase_orders.models import DeliveryRecord, PurchaseOrder, PurchaseOrderLine
from apps.suppliers.models import SupplierEvaluation, SupplierRelationship

SEED_VERSION = "2026-10-14"
DEMO_PASSWORD = "Demo@2026"  # chỉ cho môi trường demo

COMPANIES = [
    ("vnpt", "VNPT Media", "0100000001", Company.CompanyType.BUYER, ""),
    ("tech", "TechVision", "0200000002", Company.CompanyType.SUPPLIER, "IT hardware"),
    ("digi", "Digital Supply", "0300000003", Company.CompanyType.SUPPLIER, "IT hardware"),
    ("other", "Other Buyer", "0400000004", Company.CompanyType.BUYER, ""),
]

USERS = [
    ("buyer@vnptmedia.demo", "vnpt", "Buyer VNPT Media", ["BUYER"]),
    ("manager@vnptmedia.demo", "vnpt", "Manager VNPT Media", ["MANAGER"]),
    ("admin@vnptmedia.demo", "vnpt", "Admin VNPT Media", ["COMPANY_ADMIN"]),
    ("finance@vnptmedia.demo", "vnpt", "Finance VNPT Media", ["FINANCE"]),
    ("sales@techvision.demo", "tech", "Sales TechVision", ["SUPPLIER"]),
    ("sales@digitalsupply.demo", "digi", "Sales Digital Supply", ["SUPPLIER"]),
    ("buyer@otherbuyer.demo", "other", "Buyer Other Buyer", ["BUYER"]),
    ("sysadmin@procurehub.demo", None, "System Admin", ["SYSTEM_ADMIN"]),
]


def clear_all():
    for model in (
        QuotationSignature, TrustAnchor, Notification, PaymentEvent, Payment, Invoice, SupplierEvaluation, DeliveryRecord, PurchaseOrderLine, PurchaseOrder, SupplierSelection, QuotationRevision,
        QuotationLine, Quotation, RFQInvitation, RFQLine, RFQ, PurchaseRequestLine, PurchaseRequest,
        SupplierRelationship, IdempotencyKey, DocumentSequence, AuditEvent, UserRole, User, Company,
    ):
        model.objects.all().delete()


def make_pr(company, requester, status, purpose, lines, decided_by=None, budget=None, submitted_days_ago=None):
    year = timezone.now().year
    now = timezone.now()
    submitted_at = now - timedelta(days=submitted_days_ago) if submitted_days_ago is not None else None
    pr = PurchaseRequest.objects.create(
        number=DocumentSequence.next_number("PR", year), company=company, requester=requester,
        status=status, purpose=purpose, needed_by=date.today() + timedelta(days=30),
        estimated_budget=Decimal(budget) if budget else None, submitted_at=submitted_at,
        decided_by=decided_by,
        decided_at=(submitted_at + timedelta(hours=6) if submitted_at else now) if decided_by else None,
    )
    for desc, qty, unit in lines:
        PurchaseRequestLine.objects.create(request=pr, description=desc, quantity=Decimal(qty), unit=unit)
    return pr


class Command(BaseCommand):
    help = "Nạp dữ liệu demo ProcureHub (seed %s)" % SEED_VERSION

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Xóa toàn bộ dữ liệu rồi nạp lại")

    @transaction.atomic
    def handle(self, *args, **opts):
        if Company.objects.exists():
            if not opts["reset"]:
                raise CommandError("Database đã có dữ liệu. Dùng --reset để xóa rồi nạp lại.")
            clear_all()

        co = {}
        for key, name, tax, ctype, cat in COMPANIES:
            co[key] = Company.objects.create(legal_name=name, tax_code=tax, company_type=ctype, category=cat)

        users = {}
        for email, ckey, name, roles in USERS:
            u = User.objects.create_user(email, DEMO_PASSWORD, full_name=name, company=co.get(ckey))
            for r in roles:
                UserRole.objects.create(user=u, role_code=r)
            users[email] = u

        for sk in ("tech", "digi"):
            SupplierRelationship.objects.create(
                buyer_company=co["vnpt"], supplier_company=co[sk], status=SupplierRelationship.Status.ACTIVE
            )

        buyer = users["buyer@vnptmedia.demo"]
        manager = users["manager@vnptmedia.demo"]
        now = timezone.now()

        # Request APPROVED mẫu (chưa có RFQ) và request riêng của Other Buyer (kiểm thử AC-08)
        make_pr(co["vnpt"], buyer, "APPROVED", "Bàn phím và chuột cho phòng họp", [("Bàn phím", "15", "cái")], manager, budget="9000000", submitted_days_ago=1)
        make_pr(co["other"], users["buyer@otherbuyer.demo"], "DRAFT", "Mua vật tư văn phòng", [("Giấy A4", "100", "ream")])

        # Chuỗi PO COMPLETED mẫu để Dashboard có số liệu
        pr = make_pr(co["vnpt"], buyer, "APPROVED", "Laptop cho nhân viên mới", [("Laptop 14 inch", "3", "cái")], manager, budget="60000000", submitted_days_ago=14)
        rfq = RFQ.objects.create(
            number=DocumentSequence.next_number("RFQ", now.year), company=co["vnpt"], request=pr,
            title="RFQ laptop nhân viên mới", status="AWARDED", deadline=now - timedelta(days=10),
            published_at=now - timedelta(days=12),
        )
        rl = RFQLine.objects.create(rfq=rfq, source_line=pr.lines.first(), description="Laptop 14 inch", quantity=Decimal("3"), unit="cái")
        RFQInvitation.objects.create(rfq=rfq, supplier_company=co["tech"], status="QUOTED")
        price = Decimal("18000000")
        quo = Quotation.objects.create(
            rfq=rfq, supplier_company=co["tech"], status="AWARDED", revision=1, delivery_days=7,
            payment_terms="Thanh toán 30 ngày", payment_term_days=30, total=price * 3,
        )
        QuotationLine.objects.create(quotation=quo, rfq_line=rl, offered_quantity=Decimal("3"), unit_price=price, line_total=price * 3)
        revision = QuotationRevision.objects.create(
            quotation=quo, revision=1, snapshot_json={"total": str(price * 3)}, submitted_by=users["sales@techvision.demo"]
        )
        QuotationRevision.objects.filter(pk=revision.pk).update(submitted_at=now - timedelta(days=11))
        sel = SupplierSelection.objects.create(
            rfq=rfq, quotation=quo, status="APPROVED", rationale="Báo giá duy nhất đạt yêu cầu",
            proposed_by=buyer, proposed_at=now - timedelta(days=9), decided_by=manager, decided_at=now - timedelta(days=8),
        )
        po = PurchaseOrder.objects.create(
            number=DocumentSequence.next_number("PO", now.year), selection=sel, company=co["vnpt"],
            supplier_company=co["tech"], status="COMPLETED", total=price * 3, delivery_days=7,
            payment_terms="Thanh toán 30 ngày", payment_term_days=30, issued_at=now - timedelta(days=7),
            acknowledged_at=now - timedelta(days=6), delivered_at=now - timedelta(days=2),
        )
        pol = PurchaseOrderLine.objects.create(
            po=po, description="Laptop 14 inch", unit="cái", quantity=Decimal("3"), unit_price=price, line_total=price * 3
        )
        DeliveryRecord.objects.create(po_line=pol, delivered_quantity=Decimal("3"), delivered_at=now - timedelta(days=2), recorded_by=buyer)
        SupplierEvaluation.objects.create(
            purchase_order=po, buyer_company=co["vnpt"], supplier_company=co["tech"], quality_score=5,
            delivery_score=4, comment="Giao đủ, đúng cấu hình", evaluated_by=buyer,
        )
        # Hóa đơn Net 30 (VAT 10%) đã thanh toán 30% để màn Hóa đơn và Dashboard có số liệu
        invoice = Invoice.objects.create(
            number=DocumentSequence.next_number("INV", now.year), purchase_order=po, buyer_company=co["vnpt"],
            supplier_company=co["tech"], status=Invoice.Status.PARTIALLY_PAID, subtotal=po.total,
            vat_rate=Decimal("10"), vat_amount=po.total / 10, total=po.total * Decimal("1.1"),
            paid_amount=(po.total * Decimal("1.1") * Decimal("0.3")).quantize(Decimal("0.01")), issued_at=now - timedelta(days=1),
            due_date=(now - timedelta(days=1)).date() + timedelta(days=30), issued_by=users["sales@techvision.demo"],
        )
        Payment.objects.create(
            invoice=invoice, amount=invoice.paid_amount, status=Payment.Status.SUCCEEDED,
            external_ref="PAY-SEED-0001", created_by=users["finance@vnptmedia.demo"], settled_at=now - timedelta(hours=20),
        )
        seeded_events = (
            ("PR_APPROVED", manager, "procurement.purchaserequest", pr.id),
            ("SELECTION_APPROVED", manager, "procurement.supplierselection", sel.id),
            ("PO_ISSUED", buyer, "purchase_orders.purchaseorder", po.id),
            ("PO_COMPLETED", buyer, "purchase_orders.purchaseorder", po.id),
            ("INVOICE_ISSUED", users["sales@techvision.demo"], "billing.invoice", invoice.id),
        )
        for action, actor, entity_type, entity_id in seeded_events:
            AuditEvent.objects.create(
                actor=actor,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload={"seed_version": SEED_VERSION},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed {SEED_VERSION}: {Company.objects.count()} company, {User.objects.count()} user. Mật khẩu: {DEMO_PASSWORD}"
        ))
