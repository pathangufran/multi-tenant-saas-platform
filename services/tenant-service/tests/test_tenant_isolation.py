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
from apps.tenants.models import (
    Tenant,
    TenantMembership,
)
from apps.tenants.tenant_context import (
    TenantContext,
)
from apps.tenants.membership_selectors import (
    TenantMembershipSelector,
)
from apps.tenants.membership_service import (
    TenantMembershipService,
)
from django.core.exceptions import ObjectDoesNotExist

@pytest.mark.django_db
class TestTenantIsolation:

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

        TenantMembership.objects.create(
            tenant=self.tenant_a,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        self.context = TenantContext(
            tenant_id=self.tenant_a.id,
            user_id=self.user_id,
        )

        self.context_token = set_tenant_context(
            self.context,
        )

    def teardown_method(self):
        clear_tenant_context(
            self.context_token,
        )

    def test_current_tenant_id(self):
        tenant_id = (
            TenantIsolationService
            .get_current_tenant_id()
        )

        assert tenant_id == self.tenant_a.id

    def test_current_user_id(self):
        user_id = (
            TenantIsolationService
            .get_current_user_id()
        )

        assert user_id == self.user_id

    def test_current_tenant_can_access_itself(self):
        TenantIsolationService.ensure_tenant_access(
            tenant_id=self.tenant_a.id,
        )

    def test_other_tenant_is_rejected(self):
        with pytest.raises(AuthorizationError):
            TenantIsolationService.ensure_tenant_access(
                tenant_id=self.tenant_b.id,
            )

    def test_same_tenant_is_allowed(self):
        TenantIsolationService.ensure_same_tenant(
            current_tenant_id=self.tenant_a.id,
            resource_tenant_id=self.tenant_a.id,
        )

    def test_different_tenant_is_rejected(self):
        with pytest.raises(AuthorizationError):
            TenantIsolationService.ensure_same_tenant(
                current_tenant_id=self.tenant_a.id,
                resource_tenant_id=self.tenant_b.id,
            )
            
    # def test_queryset_for_tenant(self):
    #     membership_a = TenantMembership.objects.create(
    #         tenant=self.tenant_a,
    #         user_id=uuid.uuid4(),
    #         status=TenantMembership.Status.ACTIVE,
    #     )

    #     TenantMembership.objects.create(
    #         tenant=self.tenant_b,
    #         user_id=uuid.uuid4(),
    #         status=TenantMembership.Status.ACTIVE,
    #     )

    #     memberships = list(
    #         TenantMembership.objects
    #         .for_tenant(
    #             tenant_id=self.tenant_a.id,
    #         )
    #     )

    #     assert memberships == [membership_a]
        
    # def test_queryset_for_current_tenant(self):
    #     membership_a = TenantMembership.objects.create(
    #         tenant=self.tenant_a,
    #         user_id=uuid.uuid4(),
    #         status=TenantMembership.Status.ACTIVE,
    #     )

    #     TenantMembership.objects.create(
    #         tenant=self.tenant_b,
    #         user_id=uuid.uuid4(),
    #         status=TenantMembership.Status.ACTIVE,
    #     )

    #     memberships = list(
    #         TenantMembership.objects
    #         .for_current_tenant()
    #     )

    #     assert memberships == [membership_a]
        
    def test_cross_tenant_membership_update_is_rejected(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant_b,
            user_id=uuid.uuid4(),
            status=TenantMembership.Status.INVITED,
        )

        with pytest.raises(ResourceNotFoundError,):
            TenantMembershipService.activate_membership(
                membership_id=membership.id,
                tenant_id=self.tenant_a.id,
            )
            
    def test_current_tenant_membership_selector_rejects_other_tenant(
        self,
    ):
        membership = TenantMembership.objects.create(
            tenant=self.tenant_b,
            user_id=uuid.uuid4(),
            status=TenantMembership.Status.ACTIVE,
        )

        with pytest.raises(AuthorizationError):
            (
                TenantMembershipSelector
                .get_membership_for_current_tenant(
                    membership_id=membership.id,
                )
            )