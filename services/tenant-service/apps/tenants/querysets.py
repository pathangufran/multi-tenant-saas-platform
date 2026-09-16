from uuid import UUID
from django.db import models
from .isolation import TenantIsolationService

class TenantScopedQuerySet(models.QuerySet):
    
    def for_tenant(
        self,
        *,
        tenant_id: UUID
    ):
        return self.filter(
            tenant_id=tenant_id,
        )
        
    def for_current_tenant(self):
        tenant_id = (
            TenantIsolationService
            .get_current_tenant_id()
        )
        
        return self.for_tenant(
            tenant_id=tenant_id,
        )