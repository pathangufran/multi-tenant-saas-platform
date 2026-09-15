from .models import TenantMembership

class TenantMembershipSelector:
    
    @staticmethod
    def get_by_id(*,membership_id,) -> TenantMembership:
        return (
            TenantMembership.objects
            .select_related("tenant")
            .get(id=membership_id,)
        )
        
    @staticmethod
    def get_user_membership(
        *,tenant_id,user_id,
    ) -> TenantMembership:
        return (
            TenantMembership.objects
            .select_related("tenant")
            .get(
                tenant_id=tenant_id,
                user_id=user_id,
            )
        )
        
    @staticmethod
    def get_active_user_memberships(*,user_id,):
        return (
            TenantMembership.objects
            .select_related("tenant")
            .filter(
                user_id=user_id,
                status=TenantMembership.Status.ACTIVE,
            )
        )
        
    @staticmethod
    def get_active_tenant_memberships(*,tenant_id,):
        return (
            TenantMembership.objects
            .select_related("tenant")
            .filter(
                tenant_id=tenant_id,
                status=TenantMembership.Status.ACTIVE,
            )
        )