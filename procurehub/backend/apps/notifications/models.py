from django.db import models


class Notification(models.Model):
    """Hộp thư thông báo. `id` tự tăng dùng làm SSE event id; bảng đóng vai trò outbox (HLD mục 7)."""

    recipient = models.ForeignKey("identity.User", on_delete=models.CASCADE, related_name="notifications")
    company = models.ForeignKey("identity.Company", null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    event_type = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    title = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["recipient", "id"]),
            models.Index(fields=["recipient", "read_at"]),
        ]
