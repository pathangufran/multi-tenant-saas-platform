import uuid
from datetime import datetime
from .exceptions import InvalidEventError

REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "event_version",
    "occurred_at",
    "producer",
    "tenant_id",
    "aggregate_type",
    "aggregate_id",
    "aggregate_version",
    "correlation_id",
    "causation_id",
    "traceparent",
    "data",
}

def validate_event_envelope(event):
    
    if not isinstance(event, dict):
        raise InvalidEventError(
            "Event must be a JSON object."
        )

    missing_fields = REQUIRED_FIELDS - event.keys()

    if missing_fields:
        raise InvalidEventError(
            f"Missing event fields: {
                sorted(missing_fields)
            }"
        )

    try:
        uuid.UUID(str(event["event_id"]))
        uuid.UUID(str(event["correlation_id"]))

        if event["causation_id"] is not None:
            uuid.UUID(str(event["causation_id"]))

        if event["tenant_id"] is not None:
            uuid.UUID(str(event["tenant_id"]))

    except (ValueError, TypeError, AttributeError):
        raise InvalidEventError(
            "Invalid UUID in event envelope."
        )

    if (
        not isinstance(event["event_type"], str) 
        or not event["event_type"]
    ):
        raise InvalidEventError("Invalid event_type.")

    if (
        not isinstance(event["producer"], str)
        or not event["producer"]
    ):
        raise InvalidEventError("Invalid producer.")

    if (
        not isinstance(event["event_version"], int)
        or event["event_version"] < 1
    ):
        raise InvalidEventError("Invalid event_version.")

    if (
        not isinstance(event["aggregate_version"], int)
        or event["aggregate_version"] < 1
    ):
        raise InvalidEventError("Invalid aggregate_version.")

    if not isinstance(event["data"], dict):
        raise InvalidEventError("Event data must be an object.")

    if not isinstance(event["aggregate_type"], str):
        raise InvalidEventError("Invalid aggregate_type.")

    if not isinstance(event["aggregate_id"], str):
        raise InvalidEventError("Invalid aggregate_id.")

    if not isinstance(event["occurred_at"], str):
        raise InvalidEventError("Invalid occurred_at.")

    try:
        datetime.fromisoformat(
            event["occurred_at"].replace("Z", "+00:00")
        )
    except ValueError:
        raise InvalidEventError("Invalid occurred_at timestamp.")

    if event["traceparent"] is not None:
        if not isinstance(event["traceparent"], str):
            raise InvalidEventError("Invalid traceparent.")

    return event