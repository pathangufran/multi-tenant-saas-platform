import uuid
from apps.event_consumers.models import (
    TenantStatusProjection,
)

class TenantLifecycleHandler:

    STATUS_MAPPING = {
        "tenant.created": (
            TenantStatusProjection.Status.ACTIVE
        ),
        "tenant.suspended": (
            TenantStatusProjection.Status.SUSPENDED
        ),
        "tenant.activated": (
            TenantStatusProjection.Status.ACTIVE
        ),
        "tenant.deactivated": (
            TenantStatusProjection.Status.DEACTIVATED
        ),
    }
    
    @classmethod
    def handle(cls,event):
        
        event_type = event["event_type"]
        status = cls.STATUS_MAPPING.get(event_type)
        
        if status is None:
            raise ValueError(
                f"Unsupported tenant event: {event_type}"
            )
            
        data = event["data"]
        
        tenant_id = data.get("tenant_id")
        
        if not tenant_id:
            raise ValueError(
                "Tenant event is missing tenant_id."
            )
            
        try:
            tenant_id = uuid.UUID(str(tenant_id))
        
        except (ValueError,TypeError,AttributeError) as exc:
            raise ValueError(
                "Tenant event contains an invalid tenant_id."
            ) from exc
            
        return (
            TenantStatusProjection.objects.update_or_create(
                tenant_id=tenant_id,
                defaults={
                    "status": status,
                },
            )
        )