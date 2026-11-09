from django.db import IntegrityError,transaction
from apps.event_consumers.exceptions import (
    EventProcessingError,
    InvalidEventError,
)
from apps.event_consumers.models import ProcessedEvent
from apps.event_consumers.registry import (
    event_handler_registry,
)
from apps.event_consumers.validators import (
    EventValidator,
)

class EventProcessingService:
    
    @classmethod
    def process_event(cls,event):
        
        EventValidator.validate(event)
        event_id = event["event_id"]
        event_type = event["event_type"]
        
        try:
            with transaction.atomic():
                
                if ProcessedEvent.objects.filter(
                    event_id=event_id
                ).exists():
                    return {
                        "status": "DUPLICATE",
                        "event_id": event_id,
                    }
                    
                handler = event_handler_registry.get_handler(
                    event_type
                )
                
                if handler is None:
                    cls._record_event(
                        event=event,
                        status=ProcessedEvent.Status.IGNORED,
                    )
                    
                    return {
                        "status": "IGNORED",
                        "event_id": event_id,
                    }
                    
                cls._record_event(
                    event=event,
                    status=ProcessedEvent.Status.PROCESSED,
                )
                
                try:
                    handler(event)
                    
                except Exception as exc:
                    raise EventProcessingError(
                        message=(
                            f"Handler failed for event"
                            f"'{event_type}': {exc}"
                        ),
                        event_id=event_id,
                    ) from exc
                    
                return {
                    "status": "PROCESSED",
                    "event_id": event_id,
                }
                
        except IntegrityError:
            if ProcessedEvent.objects.filter(
                event_id=event_id
            ).exists():
                return {
                    "status": "DUPLICATE",
                    "event_id": event_id,
                }
                
            raise
        
    @staticmethod
    def _record_event(event,status):
        
        return ProcessedEvent.objects.create(
            event_id=event["event_id"],
            event_type=event["event_type"],
            event_version=event["event_version"],
            producer=event["producer"],
            tenant_id=event["tenant_id"],
            payload=event,
            status=status,
        )