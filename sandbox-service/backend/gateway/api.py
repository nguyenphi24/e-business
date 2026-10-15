from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth import HasMerchantApiKey
from gateway.models import Transaction
from gateway.serializers import TransactionCreateSerializer, transaction_payload
from gateway.services import resend_ipn


class TransactionListCreateView(APIView):
	permission_classes = [HasMerchantApiKey]

	def post(self, request):
		serializer = TransactionCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		existing = Transaction.objects.filter(merchant_ref=data["merchant_ref"]).first()
		if existing:
			return Response(transaction_payload(existing), status=status.HTTP_200_OK)
		created = Transaction.objects.create(**data)
		return Response(transaction_payload(created), status=status.HTTP_201_CREATED)


class TransactionDetailView(APIView):
	permission_classes = [HasMerchantApiKey]

	def get(self, request, pk):
		return Response(transaction_payload(get_object_or_404(Transaction, pk=pk)))


class TransactionResendIpnView(APIView):
	permission_classes = [HasMerchantApiKey]

	def post(self, request, pk):
		transaction = get_object_or_404(Transaction, pk=pk)
		if not transaction.last_event:
			return Response({"code": "not_completed", "message": "Transaction has no result yet."}, status=status.HTTP_409_CONFLICT)
		return Response({"event_id": transaction.last_event["event_id"], "callback_status": resend_ipn(transaction)})
