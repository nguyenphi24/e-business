from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.procurement.models import RFQInvitation
from apps.procurement.tests.flow import ProcurementFlowMixin


class InvitationResponseTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()
        self.rfq = self.open_rfq()

    def invitation(self, company):
        return RFQInvitation.objects.get(rfq_id=self.rfq["id"], supplier_company=company)

    def test_opening_rfq_marks_viewed_then_accept_notifies_buyer(self):
        self.as_user(self.tech_sales)
        self.ok(self.client.get(f"/api/v1/rfqs/{self.rfq['id']}"))
        self.assertEqual(self.invitation(self.tech).status, RFQInvitation.Status.VIEWED)

        body = self.ok(self.client.post(f"/api/v1/rfqs/{self.rfq['id']}/accept-invitation", {}, format="json"))
        self.assertEqual([item["status"] for item in body["invitations"]], ["ACCEPTED"])  # NCC chỉ thấy lời mời của mình
        self.assertIsNotNone(self.invitation(self.tech).responded_at)
        self.assertTrue(Notification.objects.filter(recipient=self.buyer, event_type="INVITATION_ACCEPTED").exists())
        again = self.client.post(f"/api/v1/rfqs/{self.rfq['id']}/accept-invitation", {}, format="json")
        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)

        self.submit_quote(self.rfq, self.tech_sales, "9000000", 10, 30)
        self.assertEqual(self.invitation(self.tech).status, RFQInvitation.Status.QUOTED)

    def test_decline_requires_reason_and_blocks_quotation(self):
        self.as_user(self.digital_sales)
        missing = self.client.post(f"/api/v1/rfqs/{self.rfq['id']}/decline-invitation", {}, format="json")
        self.assertEqual(missing.status_code, 422)
        self.ok(self.client.post(f"/api/v1/rfqs/{self.rfq['id']}/decline-invitation", {"reason": "Hết hàng"}, format="json"))
        invitation = self.invitation(self.digital)
        self.assertEqual(invitation.status, RFQInvitation.Status.DECLINED)
        self.assertEqual(invitation.decline_reason, "Hết hàng")
        self.assertTrue(Notification.objects.filter(recipient=self.buyer, event_type="INVITATION_DECLINED").exists())
        quote = self.client.post(f"/api/v1/rfqs/{self.rfq['id']}/quotation", {"lines": []}, format="json")
        self.assertEqual(quote.status_code, status.HTTP_403_FORBIDDEN)

    def test_quoting_without_explicit_accept_counts_as_accepted(self):
        self.submit_quote(self.rfq, self.tech_sales, "9000000", 10, 30)
        self.assertEqual(self.invitation(self.tech).status, RFQInvitation.Status.QUOTED)

    def test_buyer_cannot_answer_invitation(self):
        self.as_user(self.buyer)
        response = self.client.post(f"/api/v1/rfqs/{self.rfq['id']}/accept-invitation", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
