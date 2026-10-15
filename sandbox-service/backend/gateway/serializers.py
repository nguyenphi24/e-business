from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from core.callbacks import is_allowed_callback
from core.urls_utils import public_url
from gateway.models import Transaction


class TransactionCreateSerializer(serializers.Serializer):
	merchant_ref = serializers.CharField(max_length=64)
	amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("1"))
	currency = serializers.CharField(max_length=3, default="VND")
	description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
	return_url = serializers.URLField(max_length=500)
	ipn_url = serializers.URLField(max_length=500)

	def validate_ipn_url(self, value):
		if not is_allowed_callback(value):
			raise serializers.ValidationError("ipn_url is not an allowed callback URL.")
		return value

	def validate_return_url(self, value):
		if not any(value.startswith(prefix) for prefix in settings.ALLOWED_RETURN_PREFIXES):
			raise serializers.ValidationError("return_url is not an allowed return URL.")
		return value


def transaction_payload(transaction):
	return {
		"transaction_id": str(transaction.id),
		"merchant_ref": transaction.merchant_ref,
		"amount": str(transaction.amount),
		"currency": transaction.currency,
		"status": transaction.status,
		"checkout_url": public_url(f"/gateway/checkout/{transaction.id}/"),
		"created_at": transaction.created_at.isoformat(),
		"completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
	}
