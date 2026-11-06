from django.utils import timezone
from .models import FailedEvent

class FailedEventService:
    
    @staticmethod
    def record_failure(
        *,
        message,
        event,
        attempts,
        error_message,
    ):
        failed_event, _ = FailedEvent.objects.get_or_create(
            event_id=event["event_id"],
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
            defaults={
                "event_type": event["event_type"],
                "attempts": attempts,
                "error_message": error_message,
                "original_payload": event,
                "status": FailedEvent.Status.PENDING,
            },
        )
        
        return failed_event
    
    @staticmethod
    def mark_published(failed_event):
        failed_event.status = FailedEvent.Status.PUBLISHED
        failed_event.dlq_published_at = timezone.now()
        
        failed_event.save(
            update_fields=[
                "status",
                "dlq_published_at",
                "updated_at",
            ]
        )
        
    @staticmethod
    def mark_publish_failed(failed_event,error_message):
        failed_event.status = FailedEvent.Status.FAILED
        failed_event.error_message = (
            f"{failed_event.error_message}\n"
            f"DLQ publication failed: {error_message}"
        )

        failed_event.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )