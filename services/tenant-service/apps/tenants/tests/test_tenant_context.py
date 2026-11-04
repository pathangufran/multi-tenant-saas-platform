import uuid
import pytest
from apps.common.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
)
from apps.tenants.context import (
    get_tenant_context,
)
from apps.tenants.context_service import (
    TenantContextService,
)
from apps.tenants.models import (
    Tenant,
    TenantMembership,
)
from apps.tenants.context import (
    set_tenant_context,
    clear_tenant_context,
)
from apps.tenants.tenant_context import TenantContext

@pytest.mark.django_db
class TestTenantContextService:

    def setup_method(self):
        self.user_id = uuid.uuid4()

        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
        )

    def test_resolve_active_member(self):
        context = TenantContextService.resolve(
            user_id=self.user_id,
            tenant_id=self.tenant.id,
        )

        assert context.tenant_id == self.tenant.id
        assert context.user_id == self.user_id

    def test_unknown_tenant_is_rejected(self):
        with pytest.raises(ResourceNotFoundError):
            TenantContextService.resolve(
                user_id=self.user_id,
                tenant_id=uuid.uuid4(),
            )

    def test_non_member_is_rejected(self):
        another_user_id = uuid.uuid4()

        with pytest.raises(AuthorizationError):
            TenantContextService.resolve(
                user_id=another_user_id,
                tenant_id=self.tenant.id,
            )

    def test_suspended_membership_is_rejected(self):
        membership = TenantMembership.objects.get(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        membership.status = (
            TenantMembership.Status.SUSPENDED
        )

        membership.save(
            update_fields=["status"],
        )

        with pytest.raises(AuthorizationError):
            TenantContextService.resolve(
                user_id=self.user_id,
                tenant_id=self.tenant.id,
            )

    def test_removed_membership_is_rejected(self):
        membership = TenantMembership.objects.get(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        membership.status = (
            TenantMembership.Status.REMOVED
        )

        membership.save(
            update_fields=["status"],
        )

        with pytest.raises(AuthorizationError):
            TenantContextService.resolve(
                user_id=self.user_id,
                tenant_id=self.tenant.id,
            )

    def test_suspended_tenant_is_rejected(self):
        self.tenant.status = (
            Tenant.Status.SUSPENDED
        )

        self.tenant.save(
            update_fields=["status"],
        )

        with pytest.raises(AuthorizationError):
            TenantContextService.resolve(
                user_id=self.user_id,
                tenant_id=self.tenant.id,
            )

    def test_deactivated_tenant_is_rejected(self):
        self.tenant.status = (
            Tenant.Status.DEACTIVATED
        )

        self.tenant.save(
            update_fields=["status"],
        )

        with pytest.raises(AuthorizationError):
            TenantContextService.resolve(
                user_id=self.user_id,
                tenant_id=self.tenant.id,
            )
        
    def test_context_accessor_requires_context(self):
        with pytest.raises(RuntimeError):
            get_tenant_context()
            
    def test_context_is_available_inside_request_scope(self):

        context = TenantContext(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
        )

        token = set_tenant_context(context)

        try:
            current = get_tenant_context()

            assert current == context
        finally:
            clear_tenant_context(token)