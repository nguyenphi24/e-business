from django.db import models


class AuditEvent(models.Model):
    actor = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True)  # FR-AUD-04
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_events"
        indexes = [models.Index(fields=["entity_type", "entity_id", "occurred_at"])]
