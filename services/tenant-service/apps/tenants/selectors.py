from .models import Tenant

class TenantSelector:
    
    @staticmethod
    def get_by_id(
        *,
        tenant_id,
    ) -> Tenant:
        return Tenant.objects.get(
            id=tenant_id,
        )
        
    @staticmethod
    def get_by_slug(
        *,
        slug: str,
    ) -> Tenant:
        return Tenant.objects.get(
            slug__iexact=slug,
        )
        
    @staticmethod
    def get_active_tenants():
        return Tenant.objects.filter(
            status=Tenant.Status.ACTIVE,
        )