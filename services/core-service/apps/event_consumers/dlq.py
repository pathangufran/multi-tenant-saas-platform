import json
import logging
from datetime import datetime,timezone
from django.conf import settings
from kafka import KafkaProducer
from apps.event_consumers.failure_services import (
    FailedEventService,
)

logger = logging.getLogger(__name__)

class DeadLetterPublisher:
    
    def __init__(self,producer=None):
        self.producer = producer
        self._owns_producer = producer is None
        
    def create_producer(self):
        
        return KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=1,
            value_serializer=lambda value: json.dumps(
                value,
                separators=(",", ":"),
            ).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8"),
        )
        
    def _get_producer(self):
        
        if self.producer is None:
            self.producer = self.create_producer()
            
        return self.producer
    
    @staticmethod
    def build_payload(failed_event):
        
        return {
            "dlq_version": 1,
            "failed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "source": {
                "topic": failed_event.topic,
                "partition": failed_event.partition,
                "offset": failed_event.offset,
                "consumer_group": settings.KAFKA_CONSUMER_GROUP,
            },
            "failure": {
                "attempts": failed_event.attempts,
                "error_message": failed_event.error_message,
            },
            "original_event": failed_event.original_payload,
        }
        
    def publish(self, failed_event):
        
        producer = self._get_producer()
        payload = self.build_payload(failed_event)
        
        try:
            future = producer.send(
                settings.KAFKA_DLQ_TOPIC,
                key=str(failed_event.event_id),
                value=payload,
            )
            
            metadata = future.get(timeout=15)
            
            updated = FailedEventService.mark_published(
                failed_event
            )
            
            if updated != 1:
                raise RuntimeError(
                    "DLQ message was acknowledged but "
                    "the failure record could not be updated."
                )

            logger.info(
                "Event published to DLQ",
                extra={
                    "event_id": str(failed_event.event_id),
                    "topic": metadata.topic,
                    "partition": metadata.partition,
                    "offset": metadata.offset,
                },
            )

            return {
                "event_id": str(failed_event.event_id),
                "topic": metadata.topic,
                "partition": metadata.partition,
                "offset": metadata.offset,
                "status": "PUBLISHED",
            }

        except Exception as exc:
            
            FailedEventService.mark_published_failed(
                failed_event,
                str(exc),
            )
            
            logger.exception(
                "Failed to publish event to DLQ",
                extra={
                    "event_id": str(failed_event.event_id),
                },
            )
            
            raise
        
        finally:
            if self._owns_producer and self.producer is not None:
                self.close()
                
    def close(self):
        
        if self.producer is not None and self._owns_producer:
            self.producer.close()
            self.producer = None