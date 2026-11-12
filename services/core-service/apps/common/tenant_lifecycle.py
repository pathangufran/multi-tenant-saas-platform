from rest_framework.exceptions import PermissionDenied
from apps.event_consumers.models import TenantStatusProjection

class TenantLifecycleAccessService:

    @staticmethod
    def ensure_tenant_active(tenant_id):
        if not tenant_id:
            raise PermissionDenied(
                "Tenant context is required."
            )

        projection = (
            TenantStatusProjection.objects
            .filter(tenant_id=tenant_id)
            .only("status")
            .first()
        )

        if projection is None:
            raise PermissionDenied(
                "Tenant access is unavailable. "
                "Tenant lifecycle information has not been synchronized."
            )

        if projection.status != TenantStatusProjection.Status.ACTIVE:
            raise PermissionDenied(
                "This tenant is not currently active."
            )

        return projection