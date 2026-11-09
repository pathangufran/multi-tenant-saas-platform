from django.db import transaction
from django.utils import timezone
from apps.event_consumers.models import FailedEvent

class FailedEventService:
    
    @staticmethod
    @transaction.atomic
    def record_failure(
        event_id,
        event_type,
        topic,
        partition,
        offset,
        attempts,
        error_message,
        original_payload,
    ):
        
        failure_event,created = (
            FailedEvent.objects.get_or_create(
                event_id=event_id,
                topic=topic,
                partition=partition,
                offset=offset,
                defaults={
                    "event_type": event_type,
                    "attempts": attempts,
                    "error_message": error_message,
                    "original_payload": original_payload,
                    "status": FailedEvent.Status.PENDING,
                },
            )
        )
        
        if not created:
            
            FailedEvent.objects.filter(
                pk=failure_event.pk
            ).update(
                attempts=attempts,
                error_message=error_message,
                original_payload=original_payload,
                status=FailedEvent.Status.PENDING,
                dlq_published_at=None,
            )
            
            failure_event.refresh_from_db()
            
        return failure_event
    
    @staticmethod
    def mark_published(failed_event):
        
        return FailedEvent.objects.filter(
            pk=failed_event.pk,
        ).update(
            status=FailedEvent.Status.PUBLISHED,
            dlq_published_at=timezone.now(),
        )
        
    @staticmethod
    def mark_published_failed(failed_event,error_message):
        
        return FailedEvent.objects.filter(
            pk=failed_event.pk,
        ).update(
            status=FailedEvent.Status.FAILED,
            error_message=error_message,
            dlq_published_at=None,
        )