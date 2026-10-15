import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission

API_KEY_HEADER = "X-Api-Key"


class HasMerchantApiKey(BasePermission):
	"""Merchant (ProcureHub) gọi API sandbox bằng header X-Api-Key."""

	message = "Missing or invalid X-Api-Key."

	def has_permission(self, request, view):
		provided = request.headers.get(API_KEY_HEADER, "")
		return bool(provided) and hmac.compare_digest(provided, settings.SANDBOX_API_KEY)
