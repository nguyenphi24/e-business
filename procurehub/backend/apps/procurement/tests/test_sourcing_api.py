from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.identity.models import Company, User, UserRole
from apps.procurement.models import DocumentSequence, PurchaseRequest, PurchaseRequestLine, RFQ, Quotation
from apps.suppliers.models import SupplierRelationship


class SourcingApiTests(APITestCase):
    def setUp(self):
        self.buyer_company = Company.objects.create(
            legal_name="Buyer Co", tax_code="2000000001", company_type=Company.CompanyType.BUYER
        )
        self.tech = Company.objects.create(
            legal_name="Tech Co", tax_code="2000000002", company_type=Company.CompanyType.SUPPLIER, category="IT"
        )
        self.digital = Company.objects.create(
            legal_name="Digital Co", tax_code="2000000003", company_type=Company.CompanyType.SUPPLIER, category="IT"
        )
        self.buyer = self._user("buyer@sourcing.test", self.buyer_company, "BUYER")
        self.manager = self._user("manager@sourcing.test", self.buyer_company, "MANAGER")
        self.tech_sales = self._user("sales@tech.test", self.tech, "SUPPLIER")
        self.digital_sales = self._user("sales@digital.test", self.digital, "SUPPLIER")
        for supplier in (self.tech, self.digital):
            SupplierRelationship.objects.create(
                buyer_company=self.buyer_company,
                supplier_company=supplier,
                status=SupplierRelationship.Status.ACTIVE,
            )

    def _user(self, email, company, role):
        user = User.objects.create_user(email=email, password="Demo@2026", company=company, full_name=email)
        UserRole.objects.create(user=user, role_code=role)
        return user

    def _login(self, user):
        response = self.client.post(
            "/api/v1/auth/login", {"email": user.email, "password": "Demo@2026"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def _approved_request(self):
        self._login(self.buyer)
        created = self.client.post(
            reverse("purchase-request-list"),
            {
                "purpose": "IT equipment",
                "needed_by": str(date.today() + timedelta(days=30)),
                "currency": "VND",
                "lines": [{"description": "Monitor", "quantity": "2", "unit": "piece"}],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        request_id = created.data["id"]
        self.assertEqual(self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json").status_code, status.HTTP_200_OK)
        self._login(self.manager)
        approved = self.client.post(f"/api/v1/purchase-requests/{request_id}/approve", {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        return request_id

    def _create_open_rfq(self):
        request_id = self._approved_request()
        self._login(self.buyer)
        created = self.client.post(
            reverse("rfq-list"),
            {
                "request_id": request_id,
                "title": "Monitor sourcing",
                "deadline": (timezone.now() + timedelta(days=2)).isoformat(),
                "supplier_company_ids": [str(self.tech.id), str(self.digital.id)],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        rfq_id = created.data["id"]
        published = self.client.post(f"/api/v1/rfqs/{rfq_id}/publish", {}, format="json")
        self.assertEqual(published.status_code, status.HTTP_200_OK)
        return rfq_id, published.data["lines"]

    def _submit_supplier_quote(self, user, rfq_id, rfq_lines, price):
        self._login(user)
        created = self.client.post(
            f"/api/v1/rfqs/{rfq_id}/quotation",
            {
                "delivery_days": 5,
                "payment_terms": "30 days",
                "lines": [
                    {"rfq_line_id": line["id"], "offered_quantity": str(line["quantity"]), "unit_price": str(price)}
                    for line in rfq_lines
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        quotation_id = created.data["id"]
        submitted = self.client.post(f"/api/v1/quotations/{quotation_id}/submit", {}, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        return quotation_id

    def test_supplier_scope_and_full_quotation_submission(self):
        rfq_id, rfq_lines = self._create_open_rfq()
        quotation_id = self._submit_supplier_quote(self.tech_sales, rfq_id, rfq_lines, "1000000")

        self._login(self.digital_sales)
        detail = self.client.get(f"/api/v1/rfqs/{rfq_id}")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail.data["invitations"]), 1)
        self.assertNotEqual(detail.data["invitations"][0]["supplier_company"], str(self.tech.id))

        self._login(self.buyer)
        close = self.client.post(f"/api/v1/rfqs/{rfq_id}/close", {}, format="json")
        self.assertEqual(close.status_code, status.HTTP_200_OK)
        comparison = self.client.get(f"/api/v1/rfqs/{rfq_id}/comparison")
        self.assertEqual(comparison.status_code, status.HTTP_200_OK)
        self.assertEqual([str(item["id"]) for item in comparison.data["quotations"]], [quotation_id])

    def test_supplier_cannot_create_rfq_from_an_approved_request(self):
        request_id = self._approved_request()
        self._login(self.tech_sales)

        response = self.client.post(
            reverse("rfq-list"),
            {
                "request_id": request_id,
                "title": "Supplier-created RFQ",
                "deadline": (timezone.now() + timedelta(days=2)).isoformat(),
                "supplier_company_ids": [str(self.digital.id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_selection_requires_manager_and_awards_rfq(self):
        rfq_id, rfq_lines = self._create_open_rfq()
        quotation_id = self._submit_supplier_quote(self.tech_sales, rfq_id, rfq_lines, "1000000")
        self._submit_supplier_quote(self.digital_sales, rfq_id, rfq_lines, "1100000")

        self._login(self.buyer)
        self.assertEqual(self.client.post(f"/api/v1/rfqs/{rfq_id}/close", {}, format="json").status_code, status.HTTP_200_OK)
        proposed = self.client.post(
            f"/api/v1/rfqs/{rfq_id}/selection",
            {"quotation_id": quotation_id, "rationale": "Lower total price"},
            format="json",
        )
        self.assertEqual(proposed.status_code, status.HTTP_201_CREATED)
        selection_id = proposed.data["id"]

        self._login(self.manager)
        approved = self.client.post(f"/api/v1/selections/{selection_id}/approve", {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data["status"], "APPROVED")
        self.assertEqual(RFQ.objects.get(pk=rfq_id).status, RFQ.Status.AWARDED)
        self.assertEqual(Quotation.objects.get(pk=quotation_id).status, Quotation.Status.AWARDED)

    def test_purchase_order_happy_path_is_idempotent(self):
        rfq_id, rfq_lines = self._create_open_rfq()
        quotation_id = self._submit_supplier_quote(self.tech_sales, rfq_id, rfq_lines, "1000000")
        self._submit_supplier_quote(self.digital_sales, rfq_id, rfq_lines, "1100000")

        self._login(self.buyer)
        self.client.post(f"/api/v1/rfqs/{rfq_id}/close", {}, format="json")
        proposed = self.client.post(
            f"/api/v1/rfqs/{rfq_id}/selection",
            {"quotation_id": quotation_id, "rationale": "Lower total price"},
            format="json",
        )
        self._login(self.manager)
        self.client.post(f"/api/v1/selections/{proposed.data['id']}/approve", {}, format="json")

        self._login(self.buyer)
        first = self.client.post(
            "/api/v1/purchase-orders/generate",
            {"selection_id": proposed.data["id"]},
            HTTP_IDEMPOTENCY_KEY="po-test-key",
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(
            "/api/v1/purchase-orders/generate",
            {"selection_id": proposed.data["id"]},
            HTTP_IDEMPOTENCY_KEY="po-test-key",
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["id"], first.data["id"])

        order_id = first.data["id"]
        self.assertEqual(self.client.post(f"/api/v1/purchase-orders/{order_id}/issue", {}, format="json").status_code, status.HTTP_200_OK)
        self._login(self.tech_sales)
        self.assertEqual(self.client.post(f"/api/v1/purchase-orders/{order_id}/acknowledge", {}, format="json").status_code, status.HTTP_200_OK)
        self._login(self.buyer)
        delivered = self.client.post(
            f"/api/v1/purchase-orders/{order_id}/deliveries",
            {"lines": [{"po_line_id": first.data["lines"][0]["id"], "delivered_quantity": "2"}]},
            format="json",
        )
        self.assertEqual(delivered.status_code, status.HTTP_200_OK)
        self.assertEqual(delivered.data["status"], "DELIVERED")
        completed = self.client.post(f"/api/v1/purchase-orders/{order_id}/complete", {}, format="json")
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.assertEqual(completed.data["status"], "COMPLETED")
