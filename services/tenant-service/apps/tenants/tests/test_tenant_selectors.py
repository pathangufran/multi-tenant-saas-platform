import pytest
from apps.tenants.models import Tenant
from apps.tenants.selectors import TenantSelector

@pytest.mark.django_db
class TestTenantSelector:

    def setup_method(self):
        self.active_tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        self.suspended_tenant = Tenant.objects.create(
            name="Globex Corporation",
            slug="globex",
            status=Tenant.Status.SUSPENDED,
        )

    def test_get_by_id(self):
        tenant = TenantSelector.get_by_id(
            tenant_id=self.active_tenant.id,
        )

        assert tenant.id == self.active_tenant.id

    def test_get_by_slug(self):
        tenant = TenantSelector.get_by_slug(
            slug="acme",
        )

        assert tenant.id == self.active_tenant.id

    def test_get_by_slug_is_case_insensitive(self):
        tenant = TenantSelector.get_by_slug(
            slug="ACME",
        )

        assert tenant.id == self.active_tenant.id

    def test_get_active_tenants(self):
        tenants = list(
            TenantSelector.get_active_tenants()
        )

        assert len(tenants) == 1
        assert tenants[0].id == self.active_tenant.id

    def test_suspended_tenant_not_returned_as_active(self):
        tenants = list(
            TenantSelector.get_active_tenants()
        )

        assert self.suspended_tenant.id not in [
            tenant.id
            for tenant in tenants
        ]