import json
import logging
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from kafka import KafkaProducer
from .models import OutboxEvent

logger = logging.getLogger(__name__)

def build_partition_key(event):
    if event.tenant_id:
        return (
            f"{event.tenant_id}:"
            f"{event.aggregate_type}:"
            f"{event.aggregate_id}"
        )

    return (
        f"{event.aggregate_type}:"
        f"{event.aggregate_id}"
    )

def build_event_envelope(event):
    return {
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "event_version": event.event_version,
        "occurred_at": event.created_at.isoformat(),
        "producer": event.producer,
        "tenant_id": (
            str(event.tenant_id)
            if event.tenant_id
            else None
        ),
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "aggregate_version": event.aggregate_version,
        "correlation_id": str(event.correlation_id),
        "causation_id": (
            str(event.causation_id)
            if event.causation_id
            else None
        ),
        "traceparent": event.traceparent,
        "data": event.data,
    }

class OutboxPublisher:
    
    LEASE_SECONDS = 60
    MAX_BACKOFF_SECONDS = 300
    
    @staticmethod
    def create_producer():
        return KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=1,
            linger_ms=10,
            value_serializer=lambda value: json.dumps(
                value
            ).encode("utf-8"),
        )
        
    @classmethod
    def claim_pending_events(cls,batch_size=100):
        
        with transaction.atomic():
            events = list(
                OutboxEvent.objects
                .select_for_update(skip_locked=True)
                .filter(
                    Q(
                        status=OutboxEvent.Status.PENDING,
                        available_at__lte=timezone.now(),
                    ) 
                    |
                    Q(
                        status=OutboxEvent.Status.PROCESSING,
                        locked_until__lte=timezone.now(),
                    )
                    .order_by("created_at")[:batch_size]
                )
            )
            
            for event in events:
                event.status = OutboxEvent.Status.PROCESSING
                event.lock_token = uuid.uuid4()
                event.locked_until = (
                    timezone.now() + timedelta(
                        seconds=cls.LEASE_SECONDS
                    )
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

        return events
    
    @staticmethod
    def mark_published(event):
        
        updated = OutboxEvent.objects.filter(
            event_id=event.event_id,
            status=OutboxEvent.Status.PROCESSING,
            lock_token=event.lock_token,
        ).update(
            status=OutboxEvent.Status.PUBLISHED,
            published_at=timezone.now(),
            locked_until=None,
            lock_token=None,
            last_error="",
            updated_at=timezone.now(),
        )
        
        return updated == 1
    
    @classmethod
    def mark_failed(cls,event,error):
        
        delay = min(
            2 ** min(event.attempts,8),
            cls.MAX_BACKOFF_SECONDS,
        )
        
        return OutboxEvent.objects.filter(
            event_id=event.event_id,
            status=OutboxEvent.Status.PROCESSING,
            lock_token=event.lock_token,
        ).update(
            status=OutboxEvent.Status.PENDING,
            available_at=(
                timezone.now() + timedelta(seconds=delay)
            ),
            locked_until=None,
            lock_token=None,
            last_error=str(error)[:10000],
            updated_at=timezone.now(),
        ) == 1
        
    @classmethod
    def release_claims(cls,events,error):
        
        for event in events:
            cls.mark_failed(event,error)
            
    @classmethod
    def publish_batch(cls,batch_size=100):
        events = cls.claim_pending_events(batch_size)
        
        if not events:
            return {
                "claimed": 0,
                "published": 0,
                "failed": 0,
            }
            
        producer = 0
        published = 0
        failed = 0
        
        try:
            producer = cls.create_producer()
            
        except Exception as exc:
            cls.release_claims(events,exc)
            
            logger.exception(
                "Could not initialize Auth Service Kafka producer."
            )

            return {
                "claimed": len(events),
                "published": 0,
                "failed": len(events),
            }
            
        try:
            for event in events:
                try:
                    payload = build_event_envelope(event)
                    
                    producer.send(
                        settings.KAFKA_EVENTS_TOPIC,
                        key=build_partition_key(event).encode("utf-8"),
                        value=payload,
                    ).get(timeout=15)
                    
                    if cls.mark_published(event):
                        published += 1
                        
                except Exception as exc:
                    cls.mark_failed(event,exc)
                    failed += 1
                    
                    logger.exception(
                        "Auth outbox event publication failed: "
                        "event_id=%s",
                        event.event_id,
                    )
                    
        finally:
            producer.close(timeout=10)
            
        return {
            "claimed": len(events),
            "published": published,
            "failed": failed,
        }