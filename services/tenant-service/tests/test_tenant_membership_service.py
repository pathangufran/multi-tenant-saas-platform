import uuid
import pytest
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from apps.tenants.models import Tenant, TenantMembership
from apps.tenants.membership_service import (
    TenantMembershipService,
)

@pytest.mark.django_db
class TestTenantMembershipService:

    def setup_method(self):
        self.user_id = uuid.uuid4()

        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

    def test_create_membership(self):
        membership = (
            TenantMembershipService.create_membership(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
            )
        )

        assert membership.tenant_id == self.tenant.id
        assert membership.user_id == self.user_id
        assert membership.status == (
            TenantMembership.Status.ACTIVE
        )
        assert membership.joined_at is not None

    def test_create_invited_membership(self):
        membership = (
            TenantMembershipService.create_membership(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                status=TenantMembership.Status.INVITED,
            )
        )

        assert membership.status == (
            TenantMembership.Status.INVITED
        )
        assert membership.joined_at is None

    def test_duplicate_membership_raises_conflict(self):
        TenantMembershipService.create_membership(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
        )

        with pytest.raises(
            ConflictError,
            match="already a member",
        ):
            TenantMembershipService.create_membership(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
            )

    def test_unknown_tenant_raises_not_found(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipService.create_membership(
                tenant_id=uuid.uuid4(),
                user_id=self.user_id,
            )

    def test_create_membership_does_not_require_auth_database(self):
        random_user_id = uuid.uuid4()

        membership = (
            TenantMembershipService.create_membership(
                tenant_id=self.tenant.id,
                user_id=random_user_id,
            )
        )

        assert membership.user_id == random_user_id

    def test_activate_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.INVITED,
        )

        result = (
            TenantMembershipService.activate_membership(
                membership_id=membership.id,
            )
        )

        assert result.status == (
            TenantMembership.Status.INVITED
        )
        assert result.joined_at is not None

    def test_suspend_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        result = (
            TenantMembershipService.suspend_membership(
                membership_id=membership.id,
            )
        )

        assert result.status == (
            TenantMembership.Status.SUSPENDED
        )

    def test_remove_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        result = (
            TenantMembershipService.remove_membership(
                membership_id=membership.id,
            )
        )

        assert result.status == (
            TenantMembership.Status.REMOVED
        )

    def test_removed_membership_cannot_be_activated(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.REMOVED,
        )

        with pytest.raises(ConflictError):
            TenantMembershipService.activate_membership(
                membership_id=membership.id,
            )

    def test_removed_membership_cannot_be_suspended(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.REMOVED,
        )

        with pytest.raises(ConflictError):
            TenantMembershipService.suspend_membership(
                membership_id=membership.id,
            )

    def test_already_removed_membership_cannot_be_removed_again(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.REMOVED,
        )

        with pytest.raises(ConflictError):
            TenantMembershipService.remove_membership(
                membership_id=membership.id,
            )