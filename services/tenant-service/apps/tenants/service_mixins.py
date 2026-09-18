from uuid import UUID
from apps.common.exceptions import (
    AuthorizationError,
)
from .isolation import TenantIsolationService

class TenantScopedServiceMixin:
    
    @staticmethod
    def get_current_tenant_id() -> UUID:
        return (
            TenantIsolationService
            .get_current_tenant_id()
        )
        
    @staticmethod
    def ensure_tenant(
        *,
        tenant_id: UUID,
    ) -> None:
        TenantIsolationService.ensure_tenant_access(
            tenant_id=tenant_id,
        )
        
    @classmethod
    def ensure_resource_tenant(
        cls,
        *,
        resource_tenant_id: UUID,
    ) -> None:
        current_tenant_id = (
            cls.get_current_tenant_id()
        )
        
        if current_tenant_id != resource_tenant_id:
            raise AuthorizationError(
                message=(
                    "Resource does not belong to "
                    "the current tenant."
                )
            )