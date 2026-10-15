from datetime import datetime, time
from uuid import UUID

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.audit.scope import get_scoped_audit_queryset
from apps.identity.permissions import IsAuthenticatedCompanyMember
from common.exceptions import DomainError


def parse_datetime_bound(value, field_name, end_of_day=False):
    parsed = parse_datetime(value)
    if parsed is None:
        parsed_date = parse_date(value)
        if parsed_date is not None:
            parsed = datetime.combine(parsed_date, time.max if end_of_day else time.min)
    if parsed is None:
        raise DomainError(
            "validation_error",
            f"{field_name} must be a valid ISO date or datetime.",
            status_code=422,
            field_errors={field_name: ["Invalid date or datetime."]},
        )
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def serialize_event(event):
    actor = None
    if event.actor_id:
        actor = {
            "id": str(event.actor_id),
            "email": event.actor.email,
            "full_name": event.actor.full_name,
        }
    return {
        "id": event.id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": str(event.entity_id),
        "actor": actor,
        "payload": event.payload,
        "request_id": event.request_id,
        "occurred_at": event.occurred_at,
    }


class AuditEventListView(APIView):
    permission_classes = [IsAuthenticatedCompanyMember]

    def get(self, request):
        queryset = get_scoped_audit_queryset(request.user).select_related("actor")

        action_name = request.query_params.get("action")
        if action_name:
            queryset = queryset.filter(action=action_name)
        entity_type = request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        entity_id = request.query_params.get("entity_id")
        if entity_id:
            try:
                UUID(entity_id)
            except ValueError as exc:
                raise DomainError(
                    "validation_error",
                    "entity_id must be a valid UUID.",
                    status_code=422,
                    field_errors={"entity_id": ["Invalid UUID."]},
                ) from exc
            queryset = queryset.filter(entity_id=entity_id)
        if request.query_params.get("from"):
            queryset = queryset.filter(
                occurred_at__gte=parse_datetime_bound(request.query_params["from"], "from")
            )
        if request.query_params.get("to"):
            queryset = queryset.filter(
                occurred_at__lte=parse_datetime_bound(request.query_params["to"], "to", end_of_day=True)
            )

        try:
            limit = int(request.query_params.get("limit", "50"))
        except ValueError as exc:
            raise DomainError(
                "validation_error",
                "limit must be a positive integer.",
                status_code=422,
                field_errors={"limit": ["Must be a positive integer."]},
            ) from exc
        if limit < 1 or limit > 100:
            raise DomainError(
                "validation_error",
                "limit must be between 1 and 100.",
                status_code=422,
                field_errors={"limit": ["Must be between 1 and 100."]},
            )

        queryset = queryset.order_by("-occurred_at", "-id")
        total = queryset.count()
        return Response({
            "count": total,
            "limit": limit,
            "results": [serialize_event(event) for event in queryset[:limit]],
        })
