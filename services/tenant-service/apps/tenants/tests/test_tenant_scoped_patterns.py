import uuid
import pytest
from apps.common.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
)
from apps.tenants.context import (
    clear_tenant_context,
    set_tenant_context,
)
from apps.tenants.isolation import (
    TenantIsolationService,
)
from apps.tenants.membership_selectors import (
    TenantMembershipSelector,
)
from apps.tenants.models import (
    Tenant,
    TenantMembership,
)
from apps.tenants.tenant_context import (
    TenantContext,
)

@pytest.mark.django_db
class TestTenantScopedPatterns:

    def setup_method(self):
        self.user_id = uuid.uuid4()

        self.tenant_a = Tenant.objects.create(
            name="Tenant A",
            slug="tenant-a",
        )

        self.tenant_b = Tenant.objects.create(
            name="Tenant B",
            slug="tenant-b",
        )

        self.membership_a = (
            TenantMembership.objects.create(
                tenant=self.tenant_a,
                user_id=self.user_id,
            )
        )

        self.membership_b = (
            TenantMembership.objects.create(
                tenant=self.tenant_b,
                user_id=uuid.uuid4(),
            )
        )

        self.token = set_tenant_context(
            TenantContext(
                tenant_id=self.tenant_a.id,
                user_id=self.user_id,
            )
        )

    def teardown_method(self):
        clear_tenant_context(self.token)

    def test_for_tenant_returns_only_matching_resource(self):
        membership = (
            TenantMembershipSelector
            .get_for_tenant(
                tenant_id=self.tenant_a.id,
                object_id=self.membership_a.id,
            )
        )

        assert membership.id == self.membership_a.id

    def test_for_tenant_cannot_return_other_tenant_resource(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipSelector.get_for_tenant(
                tenant_id=self.tenant_a.id,
                object_id=self.membership_b.id,
            )

    def test_for_current_tenant_returns_resource(self):
        membership = (
            TenantMembershipSelector
            .get_for_current_tenant(
                membership_id=self.membership_a.id,
                tenant_id=self.tenant_a.id,
            )
        )

        assert membership.id == self.membership_a.id

    def test_for_current_tenant_cannot_return_other_tenant_resource(
        self,
    ):
        with pytest.raises(AuthorizationError):
            TenantMembershipSelector.get_for_current_tenant(
                membership_id=self.membership_b.id,
                tenant_id=self.tenant_b.id,
            )

    def test_for_tenant_requires_valid_tenant(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipSelector.get_for_tenant(
                tenant_id=self.tenant_a.id,
                object_id=uuid.uuid4(),
            )

    def test_current_tenant_is_correct(self):
        tenant_id = (
            TenantIsolationService
            .get_current_tenant_id()
        )

        assert tenant_id == self.tenant_a.id