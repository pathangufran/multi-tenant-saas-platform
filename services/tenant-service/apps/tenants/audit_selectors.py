from uuid import UUID
from apps.common.exceptions import (
    ResourceNotFoundError,
)
from .models import AuditEvent

class AuditEventSelector:
    
    @staticmethod
    def get_by_id(
        *,
        event_id: UUID,
    ) -> AuditEvent:
        try:
            return AuditEvent.objects.get(
                id=event_id,
            )
        except AuditEvent.DoesNotExist:
            raise ResourceNotFoundError(
                message="Audit event not found."
            )
            
    @staticmethod
    def get_for_tenant(
        *,
        tenant_id: UUID,
    ):
        return (
            AuditEvent.objects
            .filter(tenant_id=tenant_id)
            .order_by("-created_at")
        )
        
    @staticmethod
    def get_for_tenant_and_event_type(
        *,
        tenant_id: UUID,
        event_type: str,
    ):
        return (
            AuditEvent.objects
            .filter(
                tenant_id=tenant_id,
                event_type=event_type,
            )
            .order_by("-created_at")
        )