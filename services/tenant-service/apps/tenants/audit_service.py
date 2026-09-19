from uuid import UUID
from .models import AuditEvent

class AuditEventService:
    
    @staticmethod
    def record(
        *,
        tenant_id: UUID,
        actor_user_id: UUID,
        event_type: str,
        entity_type: str,
        entity_id: UUID,
        metadata: dict | None = None,
    ) -> AuditEvent:
        return AuditEvent.objects.create(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
        )
        
    @staticmethod
    def record_tenant_event(
        *,
        tenant_id: UUID,
        actor_user_id: UUID,
        event_type: str,
        metadata: dict | None = None,
    ) -> AuditEvent:
        return AuditEventService.record(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type="tenant",
            entity_id=tenant_id,
            metadata=metadata,   
        )