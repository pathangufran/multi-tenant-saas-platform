import json
import logging
from django.conf import settings
from django.db import transaction,models
from django.utils import timezone
from kafka import KafkaProducer
from apps.event_consumers.models import FailedEvent

logger = logging.getLogger(__name__)

class FailedEventReplayService:
    
    @staticmethod
    def replay_event(failed_event_id,producer=None):
        
        owns_producer = producer is None
        
        if owns_producer:
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
                acks="all",
                retries=5,
                max_in_flight_requests_per_connection=1,
                value_serializer=lambda value: json.dumps(
                    value
                ).encode("utf-8"),
                key_serializer=lambda value: value.encode("utf-8"),
            )
            
        try:
            with transaction.atomic():
                failed_event = (
                    FailedEvent.objects
                    .select_for_update()
                    .get(id=failed_event_id)
                )
                
                if failed_event.status == FailedEvent.Status.REPLAYED:
                    return {
                        "status": "ALREADY_REPLAYED",
                        "event_id": str(failed_event.event_id),
                    }
                    
                if failed_event.status != FailedEvent.Status.PUBLISHED:
                    raise ValueError(
                        "Only DLQ-published events can be replayed."
                    )

                original_event = failed_event.original_payload

                if not isinstance(original_event, dict):
                    raise ValueError(
                        "Original event payload must be a JSON object."
                    )

                if not original_event.get("event_id"):
                    raise ValueError(
                        "Original event is missing event_id."
                    )
                    
                key = (
                    f"{original_event.get('tenant_id')}:"
                    f"{original_event.get('aggregate_type')}:"
                    f"{original_event.get('aggregate_id')}"
                )
                
                future = producer.send(
                    failed_event.topic,
                    key=key.encode("utf-8"),
                    value=original_event,
                )
                
                future.get(timeout=10)
                
                failed_event.status = FailedEvent.Status.REPLAYED
                failed_event.replayed_at = timezone.now()
                failed_event.replay_count += 1
                failed_event.last_replay_error = ""
                
                failed_event.save(
                    update_fields=[
                        "status",
                        "replayed_at",
                        "replay_count",
                        "last_replay_error",
                        "updated_at",
                    ]
                )

                return {
                    "status": "REPLAYED",
                    "event_id": str(failed_event.event_id),
                }
                
        except Exception as exc:
            
            FailedEvent.objects.filter(
                id=failed_event_id
            ).update(
                replay_count=models.F("replay_count") + 1,
                last_replay_error=str(exc),
            )
            
            logger.exception(
                "Failed event replay failed: %s",
                failed_event_id,
            )

            raise
        
        finally:
            if owns_producer:
                producer.close()
