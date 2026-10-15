from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth import HasMerchantApiKey
from esign.crypto import get_ca
from esign.models import SignRequest
from esign.serializers import SignRequestCreateSerializer, sign_request_payload
from esign.services import create_request


class CertificateAuthorityView(APIView):
	"""Khóa công khai của CA gốc — merchant ghim (pin) khóa này để xác minh chứng thư."""

	permission_classes = [AllowAny]

	def get(self, request):
		ca = get_ca()
		return Response({"issuer": ca.name, "algorithm": "Ed25519", "public_key": ca.public_key})


class SignRequestCreateView(APIView):
	permission_classes = [HasMerchantApiKey]

	def post(self, request):
		serializer = SignRequestCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		existing = SignRequest.objects.filter(external_ref=serializer.validated_data["external_ref"]).first()
		if existing:
			return Response(sign_request_payload(existing), status=status.HTTP_200_OK)
		return Response(sign_request_payload(create_request(serializer.validated_data)), status=status.HTTP_201_CREATED)


class SignRequestDetailView(APIView):
	permission_classes = [HasMerchantApiKey]

	def get(self, request, pk):
		return Response(sign_request_payload(get_object_or_404(SignRequest, pk=pk)))
