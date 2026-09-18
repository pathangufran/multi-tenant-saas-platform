from uuid import UUID
from apps.common.exceptions import (
    ResourceNotFoundError,
)
from .isolation import TenantIsolationService
from .models import TenantMembership
from .selector_mixins import (
    TenantScopedSelectorMixin,
)

class TenantMembershipSelector(
    TenantScopedSelectorMixin,
):
    model = TenantMembership

    @staticmethod
    def get_by_id(
        *,
        membership_id,
    ) -> TenantMembership:
        return (
            TenantMembership.objects
            .select_related("tenant")
            .get(
                id=membership_id,
            )
        )

    @staticmethod
    def get_user_membership(
        *,
        tenant_id: UUID,
        user_id: UUID,
    ) -> TenantMembership:
        return (
            TenantMembership.objects
            .select_related("tenant")
            .get(
                tenant_id=tenant_id,
                user_id=user_id,
            )
        )

    @classmethod
    def get_for_current_tenant(
        cls,
        *,
        tenant_id: UUID,
        membership_id,
    ) -> TenantMembership:
        return super().get_for_current_tenant(
            object_id=membership_id,
            tenant_id=tenant_id,
        )

    @staticmethod
    def get_active_user_memberships(
        *,
        user_id: UUID,
    ):
        return (
            TenantMembership.objects
            .select_related("tenant")
            .filter(
                user_id=user_id,
                status=TenantMembership.Status.ACTIVE,
            )
        )

    @staticmethod
    def get_active_tenant_memberships(
        *,
        tenant_id: UUID,
    ):
        return (
            TenantMembership.objects
            .filter(
                tenant_id=tenant_id,
                status=TenantMembership.Status.ACTIVE,
            )
        )