from rest_framework import serializers

from apps.billing.models import Invoice, Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "amount", "status", "provider", "external_ref", "gateway_transaction_id", "checkout_url",
            "settled_at", "failure_reason", "created_at",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    purchase_order = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    balance = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    payment_term_days = serializers.SerializerMethodField()
    einvoice = serializers.SerializerMethodField()
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "purchase_order", "buyer", "supplier", "status", "currency", "subtotal", "vat_rate",
            "vat_amount", "total", "paid_amount", "balance", "is_overdue", "issued_at", "due_date", "payment_term_days",
            "note", "cancelled_at", "einvoice", "created_at", "updated_at", "payments",
        ]

    def get_purchase_order(self, invoice):
        return {"id": str(invoice.purchase_order_id), "number": invoice.purchase_order.number}

    def get_buyer(self, invoice):
        return {"id": str(invoice.buyer_company_id), "legal_name": invoice.buyer_company.legal_name}

    def get_supplier(self, invoice):
        return {"id": str(invoice.supplier_company_id), "legal_name": invoice.supplier_company.legal_name}

    def get_einvoice(self, invoice):
        return {
            "status": invoice.einvoice_status,
            "symbol": invoice.einvoice_symbol,
            "number": invoice.einvoice_number,
            "lookup_code": invoice.einvoice_lookup_code,
            "tax_code": invoice.einvoice_tax_code,
            "lookup_url": invoice.einvoice_lookup_url,
            "xml_url": invoice.einvoice_xml_url,
            "error": invoice.einvoice_error,
        }

    def get_payment_term_days(self, invoice):
        return invoice.purchase_order.payment_term_days


class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class SimulateSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=[Payment.Status.SUCCEEDED, Payment.Status.FAILED])
