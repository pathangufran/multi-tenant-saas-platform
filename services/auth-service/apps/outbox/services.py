import re
import uuid
from django.db import connection
from .models import OutboxEvent

EVENT_TYPE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
)

class OutboxService:
    
    @staticmethod
    def record_event(
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        aggregate_version: int,
        data: dict,
        tenant_id=None,
        correlation_id=None,
        causation_id=None,
        traceparent=None,
    ) -> OutboxEvent:
        
        if not connection.in_atomic_block:
            raise RuntimeError(
                "Outbox events must be recorded inside "
                "a database transaction."
            )
            
        if not EVENT_TYPE_PATTERN.match(event_type):
            return ValueError("Invalid event_type.")
        
        if not aggregate_type:
            raise ValueError("aggregate_type is required.")

        if not aggregate_id:
            raise ValueError("aggregate_id is required.")

        if aggregate_version < 1:
            raise ValueError("aggregate_version must be positive.")

        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary.")
            
        if correlation_id is not None:
            correlation_id = uuid.UUID(str(correlation_id))
        
        if causation_id is not None:
            causation_id = uuid.UUID(str(causation_id))
            
        if tenant_id is not None:
            tenant_id = uuid.UUID(str(tenant_id))
            
        return OutboxEvent.objects.create(
            event_type=event_type,
            event_version=1,
            producer="auth-service",
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            aggregate_version=aggregate_version,
            correlation_id=correlation_id or uuid.uuid4(),
            causation_id=causation_id,
            traceparent=traceparent,
            data=data,
        )