from uuid import UUID
from .models import Tenant
from .isolation import (
    TenantIsolationService,
)

class TenantQueryService:

    @staticmethod
    def get_tenant(
        *,
        tenant_id: UUID,
    ) -> Tenant:
        return Tenant.objects.get(
            id=tenant_id,
        )

    @staticmethod
    def get_current_tenant() -> Tenant:

        tenant_id = (
            TenantIsolationService
            .get_current_tenant_id()
        )

        return Tenant.objects.get(
            id=tenant_id,
        )