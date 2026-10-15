from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def vnd(value):
	try:
		amount = Decimal(str(value))
	except (InvalidOperation, ValueError):
		return value
	integer = f"{amount.quantize(Decimal('1')):,}".replace(",", ".")
	return integer


@register.filter
def qty(value):
	"""Số lượng kiểu Việt Nam: bỏ phần thập phân thừa, dấu phẩy thập phân (10.000 → 10; 2.500 → 2,5)."""
	try:
		amount = Decimal(str(value))
	except (InvalidOperation, ValueError):
		return value
	if amount == amount.to_integral_value():
		return f"{int(amount):,}".replace(",", ".")
	integer, fraction = f"{amount:f}".rstrip("0").split(".")
	return f"{int(integer):,}".replace(",", ".") + "," + fraction
