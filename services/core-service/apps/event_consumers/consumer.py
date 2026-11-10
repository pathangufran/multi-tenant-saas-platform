import json
import logging
import time
import uuid
from kafka import KafkaConsumer,KafkaError
from django.conf import settings
from apps.event_consumers.dlq import DeadLetterPublisher
from apps.event_consumers.exceptions import (
    InvalidEventError,
)
from apps.event_consumers.failure_services import (
    FailedEventService,
)
from apps.event_consumers.retry import RetryPolicy
from apps.event_consumers.services import (
    EventProcessingService,
)

logger = logging.getLogger(__name__)

class CoreEventConsumer:
    
    def __init__(
        self,
        consumer=None,
        dlq_publisher=None,
    ):
        self.consumer = consumer
        self.dlq_publisher = (
            dlq_publisher or DeadLetterPublisher()
        )
        self._running = False
        
    def create_consumer(self):
        
        return KafkaConsumer(
            settings.KAFKA_EVENTS_TOPIC,
            bootstrap_servers=(
                settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            ),
            group_id=settings.KAFKA_CONSUMER_GROUP,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=1,
            value_deserializer=lambda value: json.loads(
                value.decode("utf-8")
            ),
        )
        
    def process_message(self,message):
        
        return EventProcessingService.process_event(
            message.value
        )
        
    def commit_message(self):
        
        self.consumer.commit()
        
    def retry_message(self,attempt):
        
        if not RetryPolicy.should_retry(attempt):
            return False
        
        delay = RetryPolicy.get_delay(attempt)
        
        logger.warning(
            "Retrying Kafka event",
            extra={
                "attempt": attempt,
                "delay": delay,
            },
        )

        time.sleep(delay)

        return True
    
    @staticmethod
    def _normalize_payload(payload):
        
        if isinstance(payload,dict):
            return payload
        
        return {
            "raw_value": payload,
        }
        
    @staticmethod
    def _get_failure_event_id(payload,message):
        
        if isinstance(payload,dict):
            event_id = payload.get("event_id")
            
            if event_id:
                try:
                    return uuid.UUID(str(event_id))

                except (ValueError,TypeError,AttributeError):
                    pass
                
        source = (
            f"{message.topic}:"
            f"{message.partition}:"
            f"{message.offset}"
        )
        
        return uuid.uuid5(
            uuid.NAMESPACE_URL,
            source,
        )
        
    def send_to_dlq(
        self,
        message,
        attempts,
        error,
    ):
        
        original_payload = self._normalize_payload(
            message.value
        )
        
        event_id = self._get_failure_event_id(
            message.value,
            message,
        )
        
        event_type = original_payload.get(
            "event_type",
            "unknown",
        )

        if (
            not isinstance(event_type, str) or
            not event_type.strip()
        ):
            event_type = "unknown"

        failed_event = FailedEventService.record_failure(
            event_id=event_id,
            event_type=event_type,
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
            attempts=attempts,
            error_message=str(error),
            original_payload=original_payload,
        )
        
        return self.dlq_publisher.publish(
            failed_event
        )
        
    def handle_message(self,message):
        
        max_retries = settings.KAFKA_MAX_RETRIES
        
        if max_retries < 1:
            return ValueError(
                "KAFKA_MAX_RETRIES must be at least 1."
            )
            
        last_error = None
        
        for attempt in range(1,max_retries+1):
            try:
                
                result = self.process_message(message)
                self.commit_message()
                
                logger.info(
                    "Kafka event processed",
                    extra={
                        "event_id": result.get("event_id"),
                        "status": result.get("status"),
                    },
                )

                return result
            
            except InvalidEventError as exc:
                
                last_error = exc
                
                logger.warning(
                    "Invalid Kafka event",
                    extra={
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "error": str(exc),
                    },
                )

                break
            
            except Exception as exc:

                last_error = exc

                logger.exception(
                    "Kafka event processing failed",
                    extra={
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "attempt": attempt,
                    },
                )

                if attempt < max_retries:
                    self.retry_message(attempt)

        dlq_result = self.send_to_dlq(
            message=message,
            attempts=attempt,
            error=last_error,
        )
        
        self.commit_message()
        
        return {
            "status": "DLQ_PUBLISHED",
            "event_id": dlq_result["event_id"],
            "dlq": dlq_result,
        }

    def run(self):
        
        if self.consumer is None:
            self.consumer = self.create_consumer()
            
        self._running = True
        
        logger.info(
            "Core Kafka consumer started",
            extra={
                "topic": settings.KAFKA_EVENTS_TOPIC,
                "group": settings.KAFKA_CONSUMER_GROUP,
            },
        )

        try:
            
            while self._running:
                records = self.consumer.poll(
                    timeout_ms=1000,
                    max_records=1,
                )
                
                for messages in records.values():
                    for message in messages:
                        if not self._running:
                            break
                        
                        self.handle_message(message)
                        
        except KeyboardInterrupt:

            logger.info("Core Kafka consumer interrupted.")

        except KafkaError:

            logger.exception(
                "Kafka consumer encountered an error."
            )
            raise
        
        finally:
            self.close()
            
    def stop(self):
        
        self._running = False
        
    def close(self):
        
        if self.consumer is not None:
            self.consumer.close()
            self.consumer = None
            
        if self.dlq_publisher is not None:
            self.dlq_publisher.close()
            