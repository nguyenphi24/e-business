from apps.audit.models import AuditEvent
from common.request_context import get_request_id


def audit(actor, action_name, entity, payload=None):
    AuditEvent.objects.create(
        actor=actor,
        action=action_name,
        entity_type=entity._meta.label_lower,
        entity_id=entity.id,
        payload=payload or {},
        request_id=get_request_id(),
    )
