import logging
import time
from prometheus_client import (
    Counter, Gauge, Histogram,
)

logger = logging.getLogger("core.event_consumer")

EVENTS_PROCESSED = Counter(
    "core_kafka_events_processed_total",
    "Total successfully processed Kafka events.",
    ["event_type"],
)

EVENTS_FAILED = Counter(
    "core_kafka_events_failed_total",
    "Total failed Kafka event processing attempts.",
    ["event_type"],
)

EVENTS_IGNORED = Counter(
    "core_kafka_events_ignored_total",
    "Total ignored Kafka events.",
    ["event_type"],
)

EVENTS_SENT_TO_DLQ = Counter(
    "core_kafka_events_dlq_total",
    "Total Kafka events sent to the dead-letter queue.",
    ["event_type"],
)

EVENTS_REPLAYED = Counter(
    "core_kafka_events_replayed_total",
    "Total successfully replayed Kafka events.",
    ["event_type"],
)

PROCESSING_DURATION = Histogram(
    "core_kafka_event_processing_duration_seconds",
    "Kafka event processing duration in seconds.",
    ["event_type"],
)

CONSUMER_HEALTH = Gauge(
    "core_kafka_consumer_healthy",
    "Whether the Core Kafka consumer is healthy.",
)

LAST_SUCCESS_TIMESTAMP = Gauge(
    "core_kafka_consumer_last_success_timestamp",
    "Unix timestamp of the last successful event processing.",
)

def record_processing_success(event_type):
    EVENTS_PROCESSED.labels(event_type=event_type).inc()
    LAST_SUCCESS_TIMESTAMP.set(time.time())

def record_processing_failure(event_type):
    EVENTS_FAILED.labels(event_type=event_type).inc()

def record_ignored_event(event_type):
    EVENTS_IGNORED.labels(event_type=event_type).inc()

def record_dlq_event(event_type):
    EVENTS_SENT_TO_DLQ.labels(event_type=event_type).inc()

def record_replayed_event(event_type):
    EVENTS_REPLAYED.labels(event_type=event_type).inc()

def observe_processing_duration(event_type, duration):
    PROCESSING_DURATION.labels(
        event_type=event_type
    ).observe(duration)

def set_consumer_health(is_healthy):
    CONSUMER_HEALTH.set(1 if is_healthy else 0)

def log_event(
    level,
    message,
    *,
    event_id=None,
    event_type=None,
    tenant_id=None,
    correlation_id=None,
    consumer_group=None,
    extra=None,
):
    logger.log(
        level,
        message,
        extra={
            "event_id": event_id,
            "event_type": event_type,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "consumer_group": consumer_group,
            **(extra or {}),
        },
    )