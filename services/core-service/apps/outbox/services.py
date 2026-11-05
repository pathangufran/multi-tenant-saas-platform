import re
import uuid
from django.db import connection,transaction
from apps.outbox.models import OutboxEvent

EVENT_TYPE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"
)

class OutboxService:
    
    @staticmethod
    def record_event(
        *,
        event_type,
        aggregate_type,
        aggregate_id,
        data,
        tenant_id=None,
        aggregate_version=1,
        correlation_id=None,
        causation_id=None,
        traceparent=None,
    ):
        if not connection.in_atomic_block:
            raise RuntimeError(
                "Outbox events must be created "
                "inside the domain database transaction."
            )
            
        if not EVENT_TYPE_PATTERN.fullmatch(event_type):
            raise ValueError(
                "Invalid event type."
            )
            
        if not aggregate_type or not aggregate_id:
            raise ValueError(
                "Aggregate type and ID are required."
            )
            
        if not isinstance(data, dict):
            raise ValueError(
                "Event data must be a dictionary."
            )

        if aggregate_version < 1:
            raise ValueError(
                "Aggregate version must be at least 1."
            )

        if traceparent is not None and len(traceparent) > 100:
            raise ValueError(
                "Invalid traceparent length."
            )
            
        return OutboxEvent.objects.create(
            event_type=event_type,
            producer="core-service",
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            aggregate_version=aggregate_version,
            correlation_id=correlation_id or uuid.uuid4(),
            causation_id=causation_id,
            traceparent=traceparent,
            data=data,
        )
            
        