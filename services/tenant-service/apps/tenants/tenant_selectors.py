from uuid import UUID
from .models import Tenant,TenantMembership

class TenantSelector:
    
    @staticmethod
    def get_user_tenants(*,user_id: UUID):
        
        return (
            Tenant.objects
            .filter(
                user_id=user_id,
                membership__status=(
                    TenantMembership.Status.ACTIVE
                )
            )
            .distinct()
        )
        
    @staticmethod
    def get_user_tenant(
        *,user_id: UUID,tenant_id: UUID
    ):
        return (
            Tenant.objects
            .filter(
                id=tenant_id,
                user_id=user_id,
                membership__status=(
                    TenantMembership.Status.ACTIVE
                )
            )
        )
