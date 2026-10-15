import re

from rest_framework import serializers

from core.callbacks import is_allowed_callback
from core.urls_utils import public_url


class SignerSerializer(serializers.Serializer):
	tax_code = serializers.CharField(max_length=20)
	name = serializers.CharField(max_length=255)


class SignRequestCreateSerializer(serializers.Serializer):
	external_ref = serializers.CharField(max_length=64)
	signer = SignerSerializer()
	document_hash = serializers.CharField(max_length=64, min_length=64)
	document_label = serializers.CharField(max_length=255)
	callback_url = serializers.URLField(max_length=500)

	def validate_document_hash(self, value):
		if not re.fullmatch(r"[0-9a-f]{64}", value):
			raise serializers.ValidationError("Must be a lowercase hex SHA-256 digest.")
		return value

	def validate_callback_url(self, value):
		if not is_allowed_callback(value):
			raise serializers.ValidationError("callback_url is not an allowed callback URL.")
		return value


def sign_request_payload(sign_request):
	return {
		"request_id": str(sign_request.id),
		"external_ref": sign_request.external_ref,
		"status": sign_request.status,
		"document_hash": sign_request.document_hash,
		"sign_url": public_url(f"/esign/sign/{sign_request.id}/"),
		"expires_at": sign_request.expires_at.isoformat(),
		"signed_at": sign_request.signed_at.isoformat() if sign_request.signed_at else None,
	}
