import pytest
from django.db import IntegrityError
from apps.tenants.models import Tenant

@pytest.mark.django_db
class TestTenantModel:
    
    def test_create_tenant(self):
        tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )
        
        assert tenant.name == "Acme Corporation"
        assert tenant.slug == "acme"
        assert tenant.status == Tenant.Status.ACTIVE
        
    def test_tenant_has_uuid_primary_key(self):
        tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        assert tenant.id is not None
        assert len(str(tenant.id)) == 36

    def test_default_status_is_active(self):
        tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        assert tenant.status == Tenant.Status.ACTIVE
        
    def test_slug_is_case_insensitive_unique(self):
        Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        with pytest.raises(IntegrityError):
            Tenant.objects.create(
                name="Another Acme",
                slug="ACME",
            )

    def test_different_slugs_are_allowed(self):
        tenant_a = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        tenant_b = Tenant.objects.create(
            name="Globex Corporation",
            slug="globex",
        )

        assert tenant_a.id != tenant_b.id
        
    def test_status_choices(self):
        assert Tenant.Status.ACTIVE == "active"
        assert Tenant.Status.SUSPENDED == "suspended"
        assert Tenant.Status.DEACTIVATED == "deactivated"

    def test_string_representation(self):
        tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        assert str(tenant) == "Acme Corporation"