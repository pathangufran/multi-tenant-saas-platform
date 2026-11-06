import json
import logging
from datetime import datetime,timezone
from django.conf import settings
from kafka import KafkaProducer
from .failure_services import FailedEventService

logger = logging.getLogger(__name__)

class DeadLetterPublisher:
    
    def __init__(self,producer=None):
        self.producer = producer
        
    def create_producer(self):
        return KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=1,
            value_serializer=lambda value: json.dumps(
                value
            ).encode("utf-8"),
        )
        
    def publish(self,failed_event):
        producer = self.producer or self.create_producer()
        
        try:
            payload = {
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
                    "error": failed_event.error_message,
                },
                "event": failed_event.original_payload,
            }
            
            future = producer.send(
                settings.KAFKA_DLQ_TOPIC,
                key=str(failed_event.event_id).encode("utf-8"),
                value=payload,
            )
            future.get(timeout=15)
            
            FailedEventService.mark_published(failed_event)
            
            logger.error(
                "Event published to DLQ: event_id=%s topic=%s",
                failed_event.event_id,
                settings.KAFKA_DLQ_TOPIC,
            )
            
        except Exception as exc:
            FailedEventService.mark_publish_failed(
                failed_event,
                str(exc),
            )
            
            logger.exception(
                "DLQ publication failed for event_id=%s",
                failed_event.event_id,
            )
            raise
        
        finally:
            if self.producer is None:
                producer.close(timeout=10)