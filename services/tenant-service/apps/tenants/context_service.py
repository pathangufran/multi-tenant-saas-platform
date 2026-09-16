from uuid import UUID
from apps.common.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
)
from .membership_selectors import (
    TenantMembershipSelector,
)
from .models import Tenant
from .tenant_context import TenantContext
from django.core.exceptions import ObjectDoesNotExist

class TenantContextService:
    
    @staticmethod
    def resolve(
        *,
        user_id: UUID,
        tenant_id: UUID,
    ) -> TenantContext:
        try:
            tenant = Tenant.objects.get(
                id=tenant_id,
            )
        except Tenant.DoesNotExist:
            raise ResourceNotFoundError(
                message="Tenant not found."
            )
            
        if tenant.status != Tenant.Status.ACTIVE:
            raise AuthorizationError(
                message="Tenant is not active."
            )
            
        try:
            membership = (
                TenantMembershipSelector
                .get_user_membership(
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            )
        except ObjectDoesNotExist:
            raise AuthorizationError(
                message=(
                    "User does not have access "
                    "to this tenant."
                )
            )
            
        if membership.status != (
            membership.Status.ACTIVE
        ):
            raise AuthorizationError(
                message=(
                    "User does not have access "
                    "to this tenant."
                )
            )
            
        return TenantContext(
            tenant_id=tenant.id,
            user_id=user_id,
        )