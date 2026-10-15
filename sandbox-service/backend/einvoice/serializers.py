from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from core.callbacks import is_allowed_callback
from core.urls_utils import public_url

ALLOWED_VAT_RATES = {Decimal("0"), Decimal("5"), Decimal("8"), Decimal("10")}
CENT = Decimal("0.01")


def money(value):
	return value.quantize(CENT, rounding=ROUND_HALF_UP)


class PartySerializer(serializers.Serializer):
	tax_code = serializers.CharField(max_length=20)
	name = serializers.CharField(max_length=255)


class LineSerializer(serializers.Serializer):
	name = serializers.CharField(max_length=255)
	unit = serializers.CharField(max_length=30)
	quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
	unit_price = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"))
	amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class EInvoiceCreateSerializer(serializers.Serializer):
	external_ref = serializers.CharField(max_length=64)
	seller = PartySerializer()
	buyer = PartySerializer()
	currency = serializers.CharField(max_length=3, default="VND")
	issue_date = serializers.DateField()
	lines = LineSerializer(many=True, allow_empty=False)
	subtotal = serializers.DecimalField(max_digits=18, decimal_places=2)
	vat_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
	vat_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
	total = serializers.DecimalField(max_digits=18, decimal_places=2)
	callback_url = serializers.URLField(max_length=500)

	def validate_callback_url(self, value):
		if not is_allowed_callback(value):
			raise serializers.ValidationError("callback_url is not an allowed callback URL.")
		return value

	def validate_vat_rate(self, value):
		if value not in ALLOWED_VAT_RATES:
			raise serializers.ValidationError("vat_rate must be one of 0, 5, 8, 10.")
		return value

	def validate(self, attrs):
		"""Nhà cung cấp hóa đơn điện tử từ chối hóa đơn có số học sai — giống hệ thống thật."""
		errors = {}
		for index, line in enumerate(attrs["lines"]):
			if money(line["quantity"] * line["unit_price"]) != line["amount"]:
				errors[f"lines[{index}].amount"] = ["Must equal quantity × unit_price."]
		subtotal = sum((line["amount"] for line in attrs["lines"]), Decimal("0"))
		if subtotal != attrs["subtotal"]:
			errors["subtotal"] = ["Must equal the sum of line amounts."]
		if money(attrs["subtotal"] * attrs["vat_rate"] / 100) != attrs["vat_amount"]:
			errors["vat_amount"] = ["Must equal subtotal × vat_rate / 100."]
		if attrs["subtotal"] + attrs["vat_amount"] != attrs["total"]:
			errors["total"] = ["Must equal subtotal + vat_amount."]
		if errors:
			raise serializers.ValidationError(errors)
		return attrs


def einvoice_payload(einvoice):
	return {
		"einvoice_id": str(einvoice.id),
		"external_ref": einvoice.external_ref,
		"symbol": einvoice.symbol,
		"number": einvoice.number,
		"lookup_code": einvoice.lookup_code,
		"status": einvoice.status,
		"tax_code": einvoice.tax_code,
		"subtotal": str(einvoice.subtotal),
		"vat_rate": str(einvoice.vat_rate),
		"vat_amount": str(einvoice.vat_amount),
		"total": str(einvoice.total),
		"lookup_url": public_url(f"/einvoice/lookup/?code={einvoice.lookup_code}"),
		"xml_url": public_url(f"/einvoice/{einvoice.lookup_code}/xml/"),
		"issued_at": einvoice.issued_at.isoformat() if einvoice.issued_at else None,
	}
