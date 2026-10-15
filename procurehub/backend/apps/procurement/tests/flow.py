"""Helper dựng luồng nghiệp vụ qua API thật cho các test Source-to-Pay (không dùng shortcut ghi database)."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status

from apps.identity.models import Company, User, UserRole
from apps.suppliers.models import SupplierRelationship


class ProcurementFlowMixin:
    def setUpFlow(self):
        self.buyer_company = Company.objects.create(legal_name="Buyer Co", tax_code="3000000001", company_type=Company.CompanyType.BUYER)
        self.other_company = Company.objects.create(legal_name="Other Co", tax_code="3000000009", company_type=Company.CompanyType.BUYER)
        self.tech = Company.objects.create(legal_name="Tech Co", tax_code="3000000002", company_type=Company.CompanyType.SUPPLIER)
        self.digital = Company.objects.create(legal_name="Digital Co", tax_code="3000000003", company_type=Company.CompanyType.SUPPLIER)
        self.buyer = self.make_user("buyer@flow.test", self.buyer_company, "BUYER")
        self.manager = self.make_user("manager@flow.test", self.buyer_company, "MANAGER")
        self.finance = self.make_user("finance@flow.test", self.buyer_company, "FINANCE")
        self.other_buyer = self.make_user("buyer@other.test", self.other_company, "BUYER")
        self.other_finance = self.make_user("finance@other.test", self.other_company, "FINANCE")
        self.tech_sales = self.make_user("sales@tech.test", self.tech, "SUPPLIER")
        self.digital_sales = self.make_user("sales@digital.test", self.digital, "SUPPLIER")
        for supplier in (self.tech, self.digital):
            SupplierRelationship.objects.create(
                buyer_company=self.buyer_company, supplier_company=supplier, status=SupplierRelationship.Status.ACTIVE
            )

    def make_user(self, email, company, role):
        user = User.objects.create_user(email=email, password="Demo@2026", company=company, full_name=email)
        UserRole.objects.create(user=user, role_code=role)
        return user

    def as_user(self, user):
        self.client.force_authenticate(user)

    def ok(self, response, expected=status.HTTP_200_OK):
        self.assertEqual(response.status_code, expected, getattr(response, "data", response))
        return response.data

    def approved_request(self, budget="25000000"):
        self.as_user(self.buyer)
        created = self.ok(self.client.post("/api/v1/purchase-requests", {
            "purpose": "IT equipment",
            "needed_by": str(date.today() + timedelta(days=30)),
            "currency": "VND",
            "estimated_budget": budget,
            "lines": [{"description": "Monitor", "quantity": "2", "unit": "piece"}],
        }, format="json"), status.HTTP_201_CREATED)
        self.ok(self.client.post(f"/api/v1/purchase-requests/{created['id']}/submit", {}, format="json"))
        self.as_user(self.manager)
        self.ok(self.client.post(f"/api/v1/purchase-requests/{created['id']}/approve", {}, format="json"))
        return created["id"]

    def open_rfq(self, weights=None):
        request_id = self.approved_request()
        self.as_user(self.buyer)
        payload = {
            "request_id": request_id,
            "title": "Monitor sourcing",
            "deadline": (timezone.now() + timedelta(days=2)).isoformat(),
            "supplier_company_ids": [str(self.tech.id), str(self.digital.id)],
        }
        if weights:
            payload["scoring_weights"] = weights
        rfq = self.ok(self.client.post("/api/v1/rfqs", payload, format="json"), status.HTTP_201_CREATED)
        self.ok(self.client.post(f"/api/v1/rfqs/{rfq['id']}/publish", {}, format="json"))
        return rfq

    def submit_quote(self, rfq, supplier_user, unit_price, delivery_days, payment_term_days):
        self.as_user(supplier_user)
        line_id = rfq["lines"][0]["id"]
        quotation = self.ok(self.client.post(f"/api/v1/rfqs/{rfq['id']}/quotation", {
            "delivery_days": delivery_days,
            "payment_term_days": payment_term_days,
            "payment_terms": f"Net {payment_term_days}",
            "lines": [{"rfq_line_id": line_id, "unit_price": unit_price}],
        }, format="json"), status.HTTP_201_CREATED)
        return self.ok(self.client.post(f"/api/v1/quotations/{quotation['id']}/submit", {}, format="json"))

    def closed_rfq_with_quotes(self):
        rfq = self.open_rfq()
        tech_quote = self.submit_quote(rfq, self.tech_sales, "9000000", 10, 30)
        digital_quote = self.submit_quote(rfq, self.digital_sales, "10000000", 3, 45)
        self.as_user(self.buyer)
        self.ok(self.client.post(f"/api/v1/rfqs/{rfq['id']}/close", {}, format="json"))
        return rfq, tech_quote, digital_quote

    def issued_po(self):
        rfq, tech_quote, _ = self.closed_rfq_with_quotes()
        self.as_user(self.buyer)
        selection = self.ok(self.client.post(f"/api/v1/rfqs/{rfq['id']}/selection", {
            "quotation_id": tech_quote["id"], "rationale": "Giá thấp nhất",
        }, format="json"), status.HTTP_201_CREATED)
        self.as_user(self.manager)
        self.ok(self.client.post(f"/api/v1/selections/{selection['id']}/approve", {}, format="json"))
        self.as_user(self.buyer)
        po = self.ok(self.client.post(
            "/api/v1/purchase-orders/generate", {"selection_id": selection["id"]}, format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ), status.HTTP_201_CREATED)
        return self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/issue", {}, format="json"))

    def delivered_po(self, complete=False):
        po = self.issued_po()
        self.as_user(self.tech_sales)
        self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/acknowledge", {}, format="json"))
        self.as_user(self.buyer)
        lines = [{"po_line_id": line["id"], "delivered_quantity": str(line["quantity"])} for line in po["lines"]]
        po = self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/deliveries", {"lines": lines}, format="json"))
        if complete:
            po = self.ok(self.client.post(f"/api/v1/purchase-orders/{po['id']}/complete", {}, format="json"))
        return po

    def money(self, value):
        return Decimal(str(value))
