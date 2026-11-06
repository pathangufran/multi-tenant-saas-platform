import uuid
import json
import logging
import time
from django.conf import settings
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from .dlq import DeadLetterPublisher
from .exceptions import InvalidEventError
from .failure_services import FailedEventService
from .retry import RetryPolicy
from .services import EventProcessingService

logger = logging.getLogger(__name__)

class NotificationEventConsumer:

    def __init__(
        self,
        consumer=None,
        dlq_publisher=None,
    ):
        self.topic = settings.KAFKA_EVENTS_TOPIC
        self.bootstrap_servers = (
            settings.KAFKA_BOOTSTRAP_SERVERS
        )
        self.group_id = settings.KAFKA_CONSUMER_GROUP

        self.consumer = consumer
        self.dlq_publisher = (
            dlq_publisher or DeadLetterPublisher()
        )

        self.running = False

    def create_consumer(self):
        return KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers.split(","),
            group_id=self.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=1,
            value_deserializer=lambda value: json.loads(
                value.decode("utf-8")
            ),
        )

    def process_message(self, message):
        return EventProcessingService.process_event(
            message.value
        )

    def commit_message(self):
        self.consumer.commit()

    def send_to_dlq(self, message, attempts, error):
        raw_event = message.value

        if isinstance(raw_event, dict):
            event_id = raw_event.get("event_id")
            event_type = raw_event.get("event_type")
            normalized_event = dict(raw_event)
        else:
            event_id = None
            event_type = None
            normalized_event = {
                "raw_payload": raw_event,
            }

        if not event_id:
            event_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{message.topic}:{message.partition}:{message.offset}",
                )
            )

        if not event_type:
            event_type = "unknown.invalid"

        normalized_event["event_id"] = event_id
        normalized_event["event_type"] = event_type

        failed_event = FailedEventService.record_failure(
            message=message,
            event=normalized_event,
            attempts=attempts,
            error_message=str(error),
        )

        self.dlq_publisher.publish(failed_event)

        # Commit only after Kafka has acknowledged the DLQ message.
        self.commit_message()

    def handle_message(self, message):
        last_error = None

        for attempt in range(1, settings.KAFKA_MAX_RETRIES + 1):
            try:
                result = self.process_message(message)

                logger.info(
                    "Event handled: event_id=%s status=%s attempt=%s",
                    result["event_id"],
                    result["status"],
                    attempt,
                )

                self.commit_message()
                return result

            except InvalidEventError as exc:
                # Invalid envelopes are not made valid by retrying.
                last_error = exc
                break

            except Exception as exc:
                last_error = exc

                if not RetryPolicy.should_retry(attempt):
                    break

                delay = RetryPolicy.get_delay(attempt)

                logger.warning(
                    "Event processing failed; retrying "
                    "event at offset=%s attempt=%s delay=%.2f error=%s",
                    message.offset,
                    attempt,
                    delay,
                    exc,
                )

                time.sleep(delay)

        self.send_to_dlq(
            message=message,
            attempts=attempt,
            error=last_error,
        )

        return {
            "status": "DLQ",
            "event_id": message.value.get("event_id"),
        }

    def run(self):
        if self.consumer is None:
            self.consumer = self.create_consumer()

        self.running = True

        logger.info(
            "Notification Kafka consumer started: topic=%s group=%s",
            self.topic,
            self.group_id,
        )

        try:
            while self.running:
                records = self.consumer.poll(
                    timeout_ms=1000,
                    max_records=1,
                )

                for _, messages in records.items():
                    for message in messages:
                        self.handle_message(message)

        except KeyboardInterrupt:
            logger.info("Kafka consumer shutdown requested.")

        except KafkaError:
            logger.exception("Kafka consumer encountered a Kafka error.")
            raise

        finally:
            self.close()

    def stop(self):
        self.running = False

    def close(self):
        if self.consumer is not None:
            self.consumer.close()
            self.consumer = None

        logger.info("Notification Kafka consumer stopped.")