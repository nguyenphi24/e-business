from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.notifications.models import Notification
from apps.procurement.tests.flow import ProcurementFlowMixin


class NotificationRuleTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()

    def events_for(self, user):
        return list(Notification.objects.filter(recipient=user).values_list("event_type", flat=True))

    def test_recipients_follow_rule_table(self):
        rfq = self.open_rfq()
        self.assertIn("PR_SUBMITTED", self.events_for(self.manager))
        self.assertIn("PR_APPROVED", self.events_for(self.buyer))
        self.assertIn("RFQ_PUBLISHED", self.events_for(self.tech_sales))
        self.assertIn("RFQ_PUBLISHED", self.events_for(self.digital_sales))
        self.assertNotIn("RFQ_PUBLISHED", self.events_for(self.buyer))  # actor không tự nhận
        self.assertEqual(self.events_for(self.other_buyer), [])

        self.submit_quote(rfq, self.tech_sales, "9000000", 10, 30)
        self.assertIn("QUOTATION_SUBMITTED", self.events_for(self.buyer))
        self.assertNotIn("QUOTATION_SUBMITTED", self.events_for(self.digital_sales))
        notification = Notification.objects.get(recipient=self.buyer, event_type="QUOTATION_SUBMITTED")
        self.assertNotIn("9000000", notification.title)
        self.assertNotIn("9000000", str(notification.payload))

    def test_inbox_is_private_and_can_be_marked_read(self):
        self.open_rfq()
        tech_notification = Notification.objects.filter(recipient=self.tech_sales).first()

        self.as_user(self.digital_sales)
        response = self.client.post(f"/api/v1/notifications/{tech_notification.id}/read", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.as_user(self.tech_sales)
        inbox = self.ok(self.client.get("/api/v1/notifications?unread=true"))
        self.assertEqual(inbox["unread_count"], 1)
        self.assertEqual({item["id"] for item in inbox["results"]}, {tech_notification.id})
        self.ok(self.client.post(f"/api/v1/notifications/{tech_notification.id}/read", {}, format="json"))
        self.assertEqual(self.ok(self.client.get("/api/v1/notifications/unread-count"))["unread_count"], 0)
        self.ok(self.client.post("/api/v1/notifications/read-all", {}, format="json"))


@override_settings(NOTIFICATION_STREAM_MAX_SECONDS=0, NOTIFICATION_STREAM_POLL_SECONDS=0)
class NotificationStreamTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()

    def read_stream(self, user, after):
        token = RefreshToken.for_user(user).access_token
        response = self.client.get(f"/api/v1/notifications/stream?after={after}", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        return b"".join(response.streaming_content).decode()

    def test_stream_requires_bearer_token(self):
        self.client.force_authenticate(None)
        response = self.client.get("/api/v1/notifications/stream")
        self.assertEqual(response.status_code, 401)

    def test_stream_replays_after_last_event_id_for_recipient_only(self):
        self.open_rfq()
        own = Notification.objects.filter(recipient=self.tech_sales).order_by("id")
        body = self.read_stream(self.tech_sales, after=0)
        self.assertIn("event: notification", body)
        self.assertIn(f"id: {own.last().id}", body)
        other_ids = Notification.objects.exclude(recipient=self.tech_sales).values_list("id", flat=True)
        for other_id in other_ids:
            self.assertNotIn(f"id: {other_id}\n", body)
        # Nối lại từ id cuối: không phát lại
        self.assertNotIn("event: notification", self.read_stream(self.tech_sales, after=own.last().id))


class RequestIdTests(ProcurementFlowMixin, APITestCase):
    def setUp(self):
        self.setUpFlow()

    def test_request_id_is_echoed_and_stored_in_audit(self):
        self.as_user(self.buyer)
        response = self.client.post("/api/v1/purchase-requests", {
            "purpose": "Trace me", "needed_by": "2030-01-01", "currency": "VND",
            "lines": [{"description": "Cable", "quantity": "1", "unit": "piece"}],
        }, format="json", HTTP_X_REQUEST_ID="demo-req-002")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response["X-Request-ID"], "demo-req-002")
        event = AuditEvent.objects.get(action="PR_CREATED", entity_id=response.data["id"])
        self.assertEqual(event.request_id, "demo-req-002")

    def test_invalid_request_id_is_replaced(self):
        self.as_user(self.buyer)
        response = self.client.get("/api/v1/dashboard", HTTP_X_REQUEST_ID="bad id with spaces")
        self.assertNotEqual(response["X-Request-ID"], "bad id with spaces")
        self.assertEqual(len(response["X-Request-ID"]), 32)
