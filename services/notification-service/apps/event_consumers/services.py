import uuid
from django.db import IntegrityError, transaction
from .exceptions import EventProcessingError
from .models import ProcessedEvent
from .registry import event_handler_registry
from .validators import validate_event_envelope

class EventProcessingService:

    @staticmethod
    @transaction.atomic
    def process_event(event):
        validate_event_envelope(event)

        event_id = uuid.UUID(event["event_id"])

        if (
            ProcessedEvent.objects
            .filter(event_id=event_id).exists()
        ):
            return {
                "status": "DUPLICATE",
                "event_id": str(event_id),
            }

        handler = event_handler_registry.get_handler(
            event["event_type"]
        )

        status = (
            ProcessedEvent.Status.PROCESSED
            if handler is not None
            else ProcessedEvent.Status.IGNORED
        )

        try:
            with transaction.atomic():
                processed_event = ProcessedEvent.objects.create(
                    event_id=event_id,
                    event_type=event["event_type"],
                    event_version=event["event_version"],
                    producer=event["producer"],
                    tenant_id=event["tenant_id"],
                    payload=event,
                    status=status,
                )

        except IntegrityError:
            if ProcessedEvent.objects.filter(event_id=event_id).exists():
                return {
                    "status": "DUPLICATE",
                    "event_id": str(event_id),
                }

            raise

        if handler is None:
            return {
                "status": "IGNORED",
                "event_id": str(event_id),
            }

        try:
            handler(event)

        except Exception as exc:
            raise EventProcessingError(
                f"Failed to process event {event_id}: {exc}"
            ) from exc

        return {
            "status": "PROCESSED",
            "event_id": str(processed_event.event_id),
        }