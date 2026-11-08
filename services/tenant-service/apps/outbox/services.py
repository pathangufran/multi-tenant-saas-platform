from uuid import UUID
from django.db import connection
from .models import OutboxEvent

class OutboxService:
    
    @staticmethod
    def record_event(
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id,
        data: dict,
        tenant_id=None,
        event_version: int = 1,
        aggregate_version: int = 1,
        correlation_id=None,
        causation_id=None,
        traceparent: str = "",
        occurred_at=None,
        producer: str = "tenant-service",
    ) -> OutboxEvent:
        
        """
        Persist an event in the current business transaction.

        The caller must execute this method inside transaction.atomic().
        """

        if not connection.in_atomic_block:
            raise RuntimeError(
                "Outbox events must be recorded inside "
                "an active database transaction."
            )

        if not event_type or not event_type.strip():
            raise ValueError("event_type is required.")

        if not aggregate_type or not aggregate_type.strip():
            raise ValueError("aggregate_type is required.")

        if aggregate_id is None or not str(aggregate_id).strip():
            raise ValueError("aggregate_id is required.")

        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary.")

        if event_version < 1:
            raise ValueError("event_version must be greater than zero.")

        if aggregate_version < 1:
            raise ValueError(
                "aggregate_version must be greater than zero."
            )

        if tenant_id is not None:
            tenant_id = UUID(str(tenant_id))

        if correlation_id is not None:
            correlation_id = UUID(str(correlation_id))

        if causation_id is not None:
            causation_id = UUID(str(causation_id))
            
        event_fields = {
            "event_type": event_type.strip(),
            "event_version": event_version,
            "producer": producer,
            "tenant_id": tenant_id,
            "aggregate_type": aggregate_type.strip(),
            "aggregate_id": str(aggregate_id),
            "aggregate_version": aggregate_version,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "traceparent": traceparent or "",
            "data": data,
        }

        if occurred_at is not None:
            event_fields["occurred_at"] = occurred_at

        return OutboxEvent.objects.create(**event_fields)