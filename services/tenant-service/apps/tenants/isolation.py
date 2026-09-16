from uuid import UUID
from apps.common.exceptions import (
    AuthorizationError,
)
from .context import get_tenant_context

class TenantIsolationService:
    
    @staticmethod
    def get_current_tenant_id() -> UUID:
        context = get_tenant_context()
        
        return context.tenant_id
    
    @staticmethod
    def get_current_user_id() -> UUID:
        context = get_tenant_context()
        
        return context.user_id
    
    @staticmethod
    def ensure_tenant_access(
        *,
        tenant_id: UUID,
    ) -> None:
        context = get_tenant_context()
        
        if context.tenant_id != tenant_id:
            raise AuthorizationError(
                message=(
                    "Resource does not belong to "
                    "the current tenant."
                )
            )
            
    @staticmethod
    def ensure_same_tenant(
        *,
        current_tenant_id: UUID,
        resource_tenant_id: UUID,
    ) -> None:
        
        if current_tenant_id != resource_tenant_id:
            raise AuthorizationError(
                message=(
                    "Resource does not belong to "
                    "the current tenant."
                )
            )