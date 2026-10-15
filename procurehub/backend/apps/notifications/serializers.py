def serialize_notification(notification):
    return {
        "id": notification.id,
        "event_type": notification.event_type,
        "entity_type": notification.entity_type,
        "entity_id": str(notification.entity_id),
        "title": notification.title,
        "payload": notification.payload,
        "read_at": notification.read_at,
        "created_at": notification.created_at,
    }
