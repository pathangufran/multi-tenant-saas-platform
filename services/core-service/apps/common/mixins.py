from rest_framework.exceptions import PermissionDenied
from apps.common.tenant_lifecycle import (
    TenantLifecycleAccessService,
)

class TenantLifecycleAccessMixin:

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        tenant_id = getattr(request, "tenant_id", None)

        if tenant_id is None:
            tenant_context = getattr(request, "tenant", None)
            tenant_id = getattr(tenant_context, "id", None)

        if tenant_id is None:
            raise PermissionDenied(
                "Tenant context is required."
            )

        TenantLifecycleAccessService.ensure_tenant_active(
            tenant_id=tenant_id
        )