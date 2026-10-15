from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.identity.models import Company, User, UserRole
from apps.suppliers.models import SupplierRelationship


class DashboardAuditApiTests(APITestCase):
    def setUp(self):
        self.buyer_company = Company.objects.create(
            legal_name="Buyer Co", tax_code="3000000001", company_type=Company.CompanyType.BUYER
        )
        self.other_company = Company.objects.create(
            legal_name="Other Co", tax_code="3000000002", company_type=Company.CompanyType.BUYER
        )
        self.supplier_company = Company.objects.create(
            legal_name="Supplier Co", tax_code="3000000003", company_type=Company.CompanyType.SUPPLIER, category="IT"
        )
        self.buyer = self._user("buyer@dashboard.test", self.buyer_company, "BUYER")
        self.manager = self._user("manager@dashboard.test", self.buyer_company, "MANAGER")
        self.other_buyer = self._user("other@dashboard.test", self.other_company, "BUYER")
        SupplierRelationship.objects.create(
            buyer_company=self.buyer_company,
            supplier_company=self.supplier_company,
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

    def _create_request(self, purpose):
        response = self.client.post(
            reverse("purchase-request-list"),
            {
                "purpose": purpose,
                "needed_by": str(date.today() + timedelta(days=14)),
                "currency": "VND",
                "lines": [{"description": "Monitor", "quantity": "2", "unit": "piece"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

    def test_dashboard_is_company_scoped_and_lists_pending_request(self):
        self._login(self.buyer)
        own_request_id = self._create_request("Own request")

        self._login(self.other_buyer)
        other_request_id = self._create_request("Other request")

        self._login(self.buyer)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["scope"]["company_id"], str(self.buyer_company.id))
        self.assertFalse(response.data["scope"]["global"])
        self.assertEqual(response.data["counts"]["purchase_requests"]["DRAFT"], 1)
        self.assertEqual(response.data["pending_count"], 1)
        self.assertEqual(response.data["pending_actions"][0]["id"], own_request_id)
        activity_ids = {item["entity_id"] for item in response.data["recent_activity"]}
        self.assertIn(own_request_id, activity_ids)
        self.assertNotIn(other_request_id, activity_ids)

    def test_manager_dashboard_lists_approval_and_audit_filters_are_scoped(self):
        self._login(self.buyer)
        request_id = self._create_request("Approval request")
        submitted = self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)

        self._login(self.manager)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard.data["pending_actions"][0]["type"], "PR_APPROVAL")
        self.assertEqual(dashboard.data["pending_actions"][0]["id"], request_id)

        audit = self.client.get(
            reverse("audit-event-list"),
            {
                "action": "PR_SUBMITTED",
                "entity_type": "procurement.purchaserequest",
                "entity_id": request_id,
                "limit": 1,
            },
        )
        self.assertEqual(audit.status_code, status.HTTP_200_OK)
        self.assertEqual(audit.data["count"], 1)
        self.assertEqual(audit.data["results"][0]["entity_id"], request_id)

        invalid_limit = self.client.get(reverse("audit-event-list"), {"limit": 101})
        self.assertEqual(invalid_limit.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(invalid_limit.data["code"], "validation_error")

        invalid_entity = self.client.get(reverse("audit-event-list"), {"entity_id": "not-a-uuid"})
        self.assertEqual(invalid_entity.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(invalid_entity.data["code"], "validation_error")

    def test_buyer_can_list_only_active_supplier_relationships(self):
        self._login(self.buyer)
        response = self.client.get("/api/v1/suppliers")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["supplier_company"]["id"], str(self.supplier_company.id))
