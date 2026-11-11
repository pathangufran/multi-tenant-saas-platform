import uuid
from django.db import transaction
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
    @transaction.atomic
    def handle(cls,event):
        
        event_type = event["event_type"]
        status = cls.STATUS_MAPPING.get(event_type)
        
        if status is None:
            raise ValueError(
                f"Unsupported tenant event: {event_type}"
            )
            
        if event["aggregate_type"] != "tenant":
            raise ValueError(
                "Tenant lifecycle event must have "
                "aggregate_type='tenant'."
            )
            
        data = event["data"]
        
        tenant_id = data.get("tenant_id")
        
        if not tenant_id:
            raise ValueError(
                "Tenant event is missing tenant_id."
            )
            
        try:
            tenant_id = uuid.UUID(str(event["aggregate_id"]))
        
        except (ValueError,TypeError,AttributeError) as exc:
            raise ValueError(
                "Invalid tenant aggregate ID."
            ) from exc
            
        payload_tenant_id = event["data"].get("tenant_id")
        
        if payload_tenant_id is None:
            raise ValueError(
                "Tenant event is missing tenant_id."
            )
            
        try:
            payload_tenant_id = uuid.UUID(
                str(payload_tenant_id)
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                "Invalid tenant_id in event payload."
            ) from exc

        if payload_tenant_id != tenant_id:
            raise ValueError(
                "Tenant ID in payload does not \
                match aggregate_id."
            )
            
        incoming_version = event["aggregate_version"]
        
        projection = (
            TenantStatusProjection.objects
            .select_for_update()
            .get(tenant_id=tenant_id)
        )
        
        if projection is None:
            
            return TenantStatusProjection.objects.create(
                tenant_id=tenant_id,
                status=status,
                aggregate_version=incoming_version,
            )
            
        if incoming_version <= projection.aggregate_version:
            return projection
        
        projection.status = status
        projection.aggregate_version = incoming_version
        
        projection.save(
            update_fields=[
                "status",
                "aggregate_version",
                "updated_at",
            ]
        )

        return projection