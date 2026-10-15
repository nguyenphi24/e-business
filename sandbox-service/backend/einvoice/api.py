from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth import HasMerchantApiKey
from einvoice.models import EInvoice
from einvoice.serializers import EInvoiceCreateSerializer, einvoice_payload
from einvoice.services import create_einvoice, issue_if_due, schedule_tax_code


class EInvoiceCreateView(APIView):
	permission_classes = [HasMerchantApiKey]

	def post(self, request):
		serializer = EInvoiceCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		existing = EInvoice.objects.filter(external_ref=serializer.validated_data["external_ref"]).first()
		if existing:
			return Response(einvoice_payload(issue_if_due(existing)), status=status.HTTP_200_OK)
		einvoice = create_einvoice(serializer.validated_data)
		schedule_tax_code(einvoice)
		einvoice.refresh_from_db()
		return Response(einvoice_payload(einvoice), status=status.HTTP_201_CREATED)


class EInvoiceDetailView(APIView):
	permission_classes = [HasMerchantApiKey]

	def get(self, request, pk):
		return Response(einvoice_payload(issue_if_due(get_object_or_404(EInvoice, pk=pk))))
