import uuid
import pytest
from apps.tenants.models import Tenant, TenantMembership
from apps.tenants.membership_selectors import (
    TenantMembershipSelector,
)

@pytest.mark.django_db
class TestTenantMembershipSelector:

    def setup_method(self):
        self.user_id = uuid.uuid4()

        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

    def test_get_by_id(self):
        membership = (
            TenantMembershipSelector.get_by_id(
                membership_id=self.membership.id,
            )
        )

        assert membership.id == self.membership.id
        assert membership.tenant.id == self.tenant.id
        assert membership.user_id == self.user_id

    def test_get_user_membership(self):
        membership = (
            TenantMembershipSelector.get_user_membership(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
            )
        )

        assert membership.id == self.membership.id

    def test_get_active_user_memberships(self):
        memberships = list(
            TenantMembershipSelector
            .get_active_user_memberships(
                user_id=self.user_id,
            )
        )

        assert len(memberships) == 1
        assert memberships[0].tenant.id == self.tenant.id

    def test_get_active_tenant_memberships(self):
        memberships = list(
            TenantMembershipSelector
            .get_active_tenant_memberships(
                tenant_id=self.tenant.id,
            )
        )

        assert len(memberships) == 1
        assert memberships[0].user_id == self.user_id

    def test_inactive_membership_is_not_returned(self):
        self.membership.status = (
            TenantMembership.Status.SUSPENDED
        )

        self.membership.save(
            update_fields=["status"],
        )

        memberships = list(
            TenantMembershipSelector
            .get_active_user_memberships(
                user_id=self.user_id,
            )
        )

        assert memberships == []

    def test_removed_membership_is_not_returned(self):
        self.membership.status = (
            TenantMembership.Status.REMOVED
        )

        self.membership.save(
            update_fields=["status"],
        )

        memberships = list(
            TenantMembershipSelector
            .get_active_user_memberships(
                user_id=self.user_id,
            )
        )

        assert memberships == []