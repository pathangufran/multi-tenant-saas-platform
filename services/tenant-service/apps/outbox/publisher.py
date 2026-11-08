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

class OutboxPublisher:
    
    DEFAULT_BATCH_SIZE = 100
    LOCK_DURATION_SECONDS = 120
    BASE_RETRY_DELAY_SECONDS = 5
    MAX_RETRY_DELAY_SECONDS = 900
    
    @staticmethod
    def _create_producer():
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            acks="all",
            retries=3,
            max_in_flight_requests_per_connection=1,
            request_timeout_ms=30000,
            max_block_ms=30000,
            value_serializer=lambda value: json.dumps(
                value,
                separators=(",", ":"),
            ).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8"),
        )
        
    @staticmethod
    def _partition_key(event: OutboxEvent) -> str:
        
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
        
    @staticmethod
    def _serialize_event(event: OutboxEvent) -> dict:
        
        return {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "event_version": event.event_version,
            "occurred_at": event.occurred_at.isoformat(),
            "producer": event.producer,
            "tenant_id": (
                str(event.tenant_id)
                if event.tenant_id
                else None
            ),
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "aggregate_version": event.aggregate_version,
            "correlation_id": (
                str(event.correlation_id)
                if event.correlation_id
                else None
            ),
            "causation_id": (
                str(event.causation_id)
                if event.causation_id
                else None
            ),
            "traceparent": event.traceparent or None,
            "data": event.data,
        }
        
    @classmethod
    def _claim_events(
        cls,
        *,
        batch_size: int,
    ) -> list:
        
        lock_expiry = timezone.now() + timedelta(
            seconds=cls.LOCK_DURATION_SECONDS,
        )
        
        claimed_events = []
        
        with transaction.atomic():
            events = list(
                OutboxEvent.objects
                .select_for_update(skip_locked=True)
                .filter(
                    Q(
                        status=OutboxEvent.Status.PENDING,
                        available_at__lte=timezone.now(),
                    )
                    | Q(
                        status=OutboxEvent.Status.PROCESSING,
                        locked_until__lte=timezone.now(),
                    )
                )
                .order_by("created_at")[:batch_size]
            )
            
            for event in events:
                token = uuid.uuid4()
                
                event.status = OutboxEvent.Status.PROCESSING
                event.locked_until = lock_expiry
                event.lock_token = token
                event.attempts += 1
                
                event.save(
                    update_fields=[
                        "status",
                        "locked_until",
                        "lock_token",
                        "attempts",
                        "updated_at",
                    ]
                )

                claimed_events.append(
                    (event, token)
                )
                
        return claimed_events
    
    @classmethod
    def _mark_published(
        cls,
        *,
        event_id,
        lock_token,
    ) -> bool:
        
        updated = OutboxEvent.objects.filter(
            event_id=event_id,
            status=OutboxEvent.Status.PROCESSING,
            lock_token=lock_token,
        ).update(
            status=OutboxEvent.Status.PUBLISHED,
            published_at=timezone.now(),
            locked_until=None,
            lock_token=None,
            last_error="",   
        )
        
        return updated == 1
    
    @classmethod
    def _schedule_retry(
        cls,
        *,
        event_id,
        lock_token,
        attempts,
        error,
    ) -> bool:
        
        delay = min(
            cls.BASE_RETRY_DELAY_SECONDS * (
                2 ** max(attempts - 1, 0),
                cls.MAX_RETRY_DELAY_SECONDS,
            )
        )
        available_at = timezone.now() + timedelta(
            seconds=delay,
        )
        
        updated = OutboxEvent.objects.filter(
            event_id=event_id,
            status=OutboxEvent.Status.PROCESSING,
            lock_token=lock_token,
        ).update(
            status=OutboxEvent.Status.PENDING,
            available_at=available_at,
            locked_until=None,
            lock_token=None,
            last_error=str(error)[:4000],
        )

        return updated == 1
    
    @classmethod
    def publish_pending_events(
        cls,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> dict:
        if batch_size < 1:
            raise ValueError(
                "batch_size must be greater than zero."
            )

        producer = cls._create_producer()

        stats = {
            "claimed": 0,
            "published": 0,
            "failed": 0,
            "lease_lost": 0,
        }

        try:
            claimed_events = cls._claim_events(
                batch_size=batch_size,
            )

            stats["claimed"] = len(claimed_events)

            topic = settings.KAFKA_EVENTS_TOPIC

            for event, lock_token in claimed_events:
                try:
                    payload = cls._serialize_event(event)
                    partition_key = cls._partition_key(event)

                    future = producer.send(
                        topic,
                        key=partition_key,
                        value=payload,
                    )

                    # Wait for broker acknowledgement.
                    future.get(timeout=30)

                    marked = cls._mark_published(
                        event_id=event.event_id,
                        lock_token=lock_token,
                    )

                    if marked:
                        stats["published"] += 1
                    else:
                        stats["lease_lost"] += 1
                        logger.warning(
                            "Outbox lease lost after publishing event %s",
                            event.event_id,
                        )

                except Exception as exc:
                    retry_scheduled = cls._schedule_retry(
                        event_id=event.event_id,
                        lock_token=lock_token,
                        attempts=event.attempts,
                        error=exc,
                    )

                    if retry_scheduled:
                        stats["failed"] += 1
                    else:
                        stats["lease_lost"] += 1

                    logger.exception(
                        "Failed to publish outbox event %s",
                        event.event_id,
                    )

            return stats

        finally:
            producer.close(timeout=10)
