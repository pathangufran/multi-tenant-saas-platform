import json
import logging
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from kafka import KafkaProducer
from apps.outbox.models import OutboxEvent

logger = logging.getLogger(__name__)

EVENT_TOPIC = "saas.events.v1"

BATCH_SIZE = 100
LEASE_SECONDS = 60
PUBLISH_TIMEOUT_SECONDS = 10

def build_partition_key(event):
    if event.tenant_id:
        return (
            f"{event.tenant_id}:"
            f"{event.aggregate_type}:"
            f"{event.aggregate_id}"
        )
        
    return f"{event.aggregate_type}:{event.aggregate_id}"

def build_event_envelope(event):
    return {
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "event_version": event.event_version,
        "occurred_at": event.created_at.isoformat(),
        "producer": event.producer,
        "tenant_id": (
            str(event.tenant_id)
            if event.tenant_id else None
        ),
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "aggregate_version": event.aggregate_version,
        "correlation_id": str(event.correlation_id),
        "causation_id": (
            str(event.causation_id)
            if event.causation_id else None
        ),
        "traceparent": event.traceparent,
        "data": event.data,
    }
    
def claim_pending_events(limit=BATCH_SIZE):
    now = timezone.now()
    events = []
    
    with transaction.atomic():
        candidates = (
            OutboxEvent.objects
            .select_for_update(skip_locked=True)
            .filter(
                Q(
                    status=OutboxEvent.Status.PENDING,
                    available_at__lte=now,
                )
                |
                Q(
                    status=OutboxEvent.Status.PROCESSING,
                    locked_until__lte=now,
                )
                .order_by("created_at")[:limit]
                
            )
        )
        
        for event in candidates:
            token = uuid.uuid4()
            
            event.status = OutboxEvent.Status.PROCESSING
            event.lock_token = token
            event.locked_until = (
                now + timedelta(seconds=LEASE_SECONDS)
            )
            event.attempts += 1
            
            event.save(
                update_fields=[
                    "status",
                    "lock_token",
                    "locked_until",
                    "attempts",
                    "updated_at",
                ]
            )
            
            events.append((event,token))
            
    return events

def mark_published(event_id,token):
    return OutboxEvent.objects.filter(
        event_id=event_id,
        status=OutboxEvent.Status.PROCESSING,
        lock_token=token,
    ).update(
        status=OutboxEvent.Status.PUBLISHED,
        published_at=timezone.now(),
        locked_until=None,
        lock_token=None,
        last_error="",
    ) == 1
    
def mark_publish_failed(event_id,token,error):
    event = OutboxEvent.objects.get(
        event_id=event_id,
        status=OutboxEvent.Status.PROCESSING,
        lock_token=token,
    )
    
    if event is None:
        return False
    
    delay_seconds = min(
        2 ** min(event.attempts, 8),
        300,
    )

    return OutboxEvent.objects.filter(
        event_id=event_id,
        status=OutboxEvent.Status.PROCESSING,
        lock_token=token,
    ).update(
        status=OutboxEvent.Status.PENDING,
        available_at=(
            timezone.now()
            + timedelta(seconds=delay_seconds)
        ),
        locked_until=None,
        lock_token=None,
        last_error=str(error)[:4000],
    ) == 1
    
def create_kafka_producer():
    bootstrap_servers = getattr(
        settings,
        "KAFKA_BOOTSTRAP_SERVERS",
        None,
    )
    
    if not bootstrap_servers:
        return RuntimeError(
            "KAFKA_BOOTSTRAP_SERVERS is not configured."
        )
        
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        acks="all",
        retries=5,
        linger_ms=10,
        request_timeout_ms=15000,
        value_serializer=lambda value: json.dumps(
            value,
            separators=(",", ":"),
        ).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )
    
def publish_pending_events(limit=BATCH_SIZE):
    claimed_events = claim_pending_events(
        limit=limit
    )
    if not claimed_events:
        return {
            "claimed": 0,
            "published": 0,
            "failed": 0,
        }
        
    producer = None
    published = 0
    failed = 0
    
    try:
        producer = create_kafka_producer()
        
        for event,token in claimed_events:
            try:
                future = producer.send(
                    EVENT_TOPIC,
                    key=build_partition_key(event),
                    value=build_event_envelope(event),
                )
                future.get(
                    timeout=PUBLISH_TIMEOUT_SECONDS,
                )
                
                if mark_published(event.event_id,token):
                    published += 1
                
            except Exception as exc:
                logger.exception(
                    "Outbox event publishing failed",
                    extra={
                        "event": "outbox.publish_failed",
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                    },
                )
                
                if mark_publish_failed(
                    event.event_id,
                    token,
                    exc,
                ):
                    failed += 1
                    
    except Exception as exc:
        logger.exception(
            "Kafka producer initialization failed",
            extra={"event": "outbox.producer_failed"},
        )

        for event, token in claimed_events:
            if mark_publish_failed(
                event.event_id,
                token,
                exc,
            ):
                failed += 1
                
    finally:
        if producer is not None:
            producer.close(timeout=10)
            
    return {
        "claimed": len(claimed_events),
        "published": published,
        "failed": failed,
    }
