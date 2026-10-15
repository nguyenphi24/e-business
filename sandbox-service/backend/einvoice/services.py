import secrets
import threading
import uuid
from datetime import timedelta
from xml.etree import ElementTree

from django.conf import settings
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models import Max
from django.utils import timezone

from core.callbacks import deliver
from einvoice.models import EInvoice
from einvoice.serializers import einvoice_payload


def create_einvoice(data):
	year = data["issue_date"].year % 100
	symbol = f"SBX{year:02d}"
	for _ in range(5):
		try:
			with transaction.atomic():
				last = EInvoice.objects.filter(symbol=symbol).aggregate(value=Max("number"))["value"] or 0
				return EInvoice.objects.create(
					external_ref=data["external_ref"],
					symbol=symbol,
					number=last + 1,
					lookup_code=secrets.token_hex(5).upper(),
					seller_tax_code=data["seller"]["tax_code"],
					seller_name=data["seller"]["name"],
					buyer_tax_code=data["buyer"]["tax_code"],
					buyer_name=data["buyer"]["name"],
					currency=data["currency"],
					subtotal=data["subtotal"],
					vat_rate=data["vat_rate"],
					vat_amount=data["vat_amount"],
					total=data["total"],
					lines=[{key: str(value) for key, value in line.items()} for line in data["lines"]],
					issue_date=data["issue_date"],
					callback_url=data["callback_url"],
				)
		except IntegrityError:
			existing = EInvoice.objects.filter(external_ref=data["external_ref"]).first()
			if existing:
				return existing
	raise RuntimeError("Could not allocate an invoice number.")


def issue_tax_code(einvoice_id):
	""""Cơ quan thuế" cấp mã cho hóa đơn rồi báo kết quả về merchant. Gọi lặp lại không cấp hai lần."""
	with transaction.atomic():
		einvoice = EInvoice.objects.select_for_update().get(pk=einvoice_id)
		if einvoice.status != EInvoice.Status.PENDING_TAX_CODE:
			return einvoice
		einvoice.status = EInvoice.Status.ISSUED
		einvoice.tax_code = f"SBX{einvoice.issue_date:%y}-{secrets.token_hex(8).upper()}"
		einvoice.issued_at = timezone.now()
		einvoice.last_event = {"event_id": f"evt_{uuid.uuid4().hex}", **einvoice_payload(einvoice)}
		einvoice.save(update_fields=["status", "tax_code", "issued_at", "last_event"])
	deliver("einvoice", einvoice.id, einvoice.callback_url, einvoice.last_event)
	return einvoice


def _issue_in_background(einvoice_id):
	try:
		issue_tax_code(einvoice_id)
	finally:
		close_old_connections()


def schedule_tax_code(einvoice):
	delay = settings.EINVOICE_TAX_DELAY_SECONDS
	if delay <= 0:
		issue_tax_code(einvoice.id)
		return
	timer = threading.Timer(delay, _issue_in_background, args=(einvoice.id,))
	timer.daemon = True
	transaction.on_commit(timer.start)


def issue_if_due(einvoice):
	"""Dự phòng khi timer bị mất (server khởi động lại): hóa đơn quá hạn chờ sẽ được cấp mã khi có người đọc."""
	if einvoice.status == EInvoice.Status.PENDING_TAX_CODE and einvoice.created_at + timedelta(seconds=settings.EINVOICE_TAX_DELAY_SECONDS) <= timezone.now():
		return issue_tax_code(einvoice.id)
	return einvoice


def build_xml(einvoice):
	root = ElementTree.Element("HoaDonGiaLap", {"canhBao": "Hoa don gia lap - khong co gia tri phap ly"})
	general = ElementTree.SubElement(root, "ThongTinChung")
	for tag, value in (
		("KyHieu", einvoice.symbol), ("SoHoaDon", str(einvoice.number)), ("NgayLap", einvoice.issue_date.isoformat()),
		("MaTraCuu", einvoice.lookup_code), ("MaCoQuanThueGiaLap", einvoice.tax_code or ""), ("DonViTienTe", einvoice.currency),
	):
		ElementTree.SubElement(general, tag).text = value
	for tag, tax_code, name in (("NguoiBan", einvoice.seller_tax_code, einvoice.seller_name), ("NguoiMua", einvoice.buyer_tax_code, einvoice.buyer_name)):
		party = ElementTree.SubElement(root, tag)
		ElementTree.SubElement(party, "MaSoThue").text = tax_code
		ElementTree.SubElement(party, "Ten").text = name
	lines = ElementTree.SubElement(root, "DanhSachHangHoa")
	for index, line in enumerate(einvoice.lines, start=1):
		item = ElementTree.SubElement(lines, "HangHoa", {"stt": str(index)})
		for tag, key in (("Ten", "name"), ("DonViTinh", "unit"), ("SoLuong", "quantity"), ("DonGia", "unit_price"), ("ThanhTien", "amount")):
			ElementTree.SubElement(item, tag).text = line[key]
	totals = ElementTree.SubElement(root, "TongTien")
	for tag, value in (("TienTruocThue", einvoice.subtotal), ("ThueSuatGTGT", einvoice.vat_rate), ("TienThueGTGT", einvoice.vat_amount), ("TongThanhToan", einvoice.total)):
		ElementTree.SubElement(totals, tag).text = str(value)
	ElementTree.indent(root)
	return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)
