from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.identity.models import Company, User, UserRole
from apps.procurement.models import PurchaseRequest


class PurchaseRequestApiTests(APITestCase):
    def setUp(self):
        self.buyer_company = Company.objects.create(
            legal_name="Buyer Co", tax_code="1000000001", company_type=Company.CompanyType.BUYER
        )
        self.other_company = Company.objects.create(
            legal_name="Other Co", tax_code="1000000002", company_type=Company.CompanyType.BUYER
        )
        self.buyer = self._user("buyer@example.test", self.buyer_company, "BUYER")
        self.manager = self._user("manager@example.test", self.buyer_company, "MANAGER")
        self.other_buyer = self._user("other@example.test", self.other_company, "BUYER")

    def _user(self, email, company, role):
        user = User.objects.create_user(email=email, password="Demo@2026", company=company, full_name=email)
        UserRole.objects.create(user=user, role_code=role)
        return user

    def _login(self, user):
        response = self.client.post(
            "/api/v1/auth/login",
            {"email": user.email, "password": "Demo@2026"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def _create_request(self):
        response = self.client.post(
            reverse("purchase-request-list"),
            {
                "purpose": "Office equipment",
                "needed_by": str(date.today() + timedelta(days=14)),
                "currency": "VND",
                "lines": [{"description": "Monitor", "quantity": "2", "unit": "piece"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def test_login_me_and_refresh_cookie(self):
        response = self._login(self.buyer)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["company"]["legal_name"], "Buyer Co")
        self.assertEqual(response.cookies["ph_refresh"]["httponly"], True)

        me = self.client.get("/api/v1/auth/me")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], self.buyer.email)

        refreshed = self.client.post("/api/v1/auth/refresh", {}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)

        logged_out = self.client.post("/api/v1/auth/logout", {}, format="json")
        self.assertEqual(logged_out.status_code, status.HTTP_204_NO_CONTENT)
        refresh_after_logout = self.client.post("/api/v1/auth/refresh", {}, format="json")
        self.assertEqual(refresh_after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_submit_and_manager_approve_request(self):
        self._login(self.buyer)
        created = self._create_request()
        request_id = created.data["id"]
        self.assertEqual(created.data["status"], PurchaseRequest.Status.DRAFT)

        submitted = self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        self.assertEqual(submitted.data["status"], PurchaseRequest.Status.PENDING_APPROVAL)

        self._login(self.manager)
        approved = self.client.post(f"/api/v1/purchase-requests/{request_id}/approve", {}, format="json")
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data["status"], PurchaseRequest.Status.APPROVED)
        self.assertTrue(AuditEvent.objects.filter(action="PR_APPROVED", entity_id=request_id).exists())

    def test_same_user_with_buyer_and_manager_role_cannot_self_approve(self):
        UserRole.objects.create(user=self.buyer, role_code="MANAGER")
        self._login(self.buyer)
        request_id = self._create_request().data["id"]
        self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")

        response = self.client.post(f"/api/v1/purchase-requests/{request_id}/approve", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "separation_of_duties")

    def test_buyer_cannot_call_manager_approval_action(self):
        self._login(self.buyer)
        request_id = self._create_request().data["id"]
        self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")

        response = self.client.post(f"/api/v1/purchase-requests/{request_id}/approve", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "permission_denied")
        self.assertEqual(PurchaseRequest.objects.get(pk=request_id).status, PurchaseRequest.Status.PENDING_APPROVAL)

    def test_reject_requires_reason_and_rejected_request_can_be_resubmitted(self):
        self._login(self.buyer)
        request_id = self._create_request().data["id"]
        self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")

        self._login(self.manager)
        missing_reason = self.client.post(f"/api/v1/purchase-requests/{request_id}/reject", {}, format="json")
        self.assertEqual(missing_reason.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(missing_reason.data["code"], "validation_error")

        rejected = self.client.post(
            f"/api/v1/purchase-requests/{request_id}/reject",
            {"reason": "Need a clearer specification"},
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.data["status"], PurchaseRequest.Status.REJECTED)

        self._login(self.buyer)
        resubmitted = self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")
        self.assertEqual(resubmitted.status_code, status.HTTP_200_OK)
        self.assertEqual(resubmitted.data["status"], PurchaseRequest.Status.PENDING_APPROVAL)

    def test_company_scope_hides_other_company_request(self):
        self._login(self.buyer)
        request_id = self._create_request().data["id"]

        self._login(self.other_buyer)
        response = self.client.get(f"/api/v1/purchase-requests/{request_id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_approval_state_returns_conflict(self):
        self._login(self.buyer)
        request_id = self._create_request().data["id"]
        self._login(self.manager)
        response = self.client.post(f"/api/v1/purchase-requests/{request_id}/approve", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "invalid_transition")

    def test_approved_request_cannot_be_submitted_or_cancelled(self):
        self._login(self.buyer)
        request_id = self._create_request().data["id"]
        self.client.post(f"/api/v1/purchase-requests/{request_id}/submit", {}, format="json")
        self._login(self.manager)
        self.assertEqual(
            self.client.post(f"/api/v1/purchase-requests/{request_id}/approve", {}, format="json").status_code,
            status.HTTP_200_OK,
        )

        self._login(self.buyer)
        for action in ("submit", "cancel"):
            response = self.client.post(f"/api/v1/purchase-requests/{request_id}/{action}", {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            self.assertEqual(response.data["code"], "invalid_transition")
