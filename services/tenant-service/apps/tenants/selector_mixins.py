from uuid import UUID
from apps.common.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
)
from .isolation import TenantIsolationService

class TenantScopedSelectorMixin:
    
    model = None
    
    @classmethod
    def get_for_tenant(
        cls,
        *,
        tenant_id: UUID,
        object_id,
    ):
        if cls.model is None:
            raise NotImplementedError(
                "Selector model must be defined."
            )
        try:  
            return cls.model.objects.get(
                id=object_id,
                tenant_id=tenant_id,
            )
        except cls.model.DoesNotExist:
            raise ResourceNotFoundError(
                message="Resource not found."
            )
        
    @classmethod
    def get_for_current_tenant(
        cls,
        *,
        tenant_id: UUID,
        object_id,
    ):
        if cls.model is None:
            raise NotImplementedError(
                "Selector model must be defined."
            )
            
        current_tenant_id = (
            TenantIsolationService.get_current_tenant_id()
        )
        
        if tenant_id != current_tenant_id:
            raise AuthorizationError(
                message="You are not authorized to access \
                this resource."
            )

        try:
            return cls.model.objects.get(
                id=object_id,
                tenant_id=tenant_id,
            )
        except cls.model.DoesNotExist:
            raise ResourceNotFoundError(
                message="Resource not found."
            )
        