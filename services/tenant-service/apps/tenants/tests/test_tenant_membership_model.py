import uuid
import pytest
from django.db import IntegrityError
from apps.tenants.models import Tenant, TenantMembership

@pytest.mark.django_db
class TestTenantMembershipModel:

    def setup_method(self):
        self.user_id = uuid.uuid4()

        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

    def test_create_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        assert membership.tenant == self.tenant
        assert membership.user_id == self.user_id
        assert membership.status == (
            TenantMembership.Status.ACTIVE
        )

    def test_membership_has_uuid_primary_key(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        assert membership.id is not None
        assert len(str(membership.id)) == 36

    def test_membership_does_not_require_auth_user_model(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=uuid.uuid4(),
        )

        assert membership.pk is not None

    def test_duplicate_membership_is_rejected(self):
        TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        with pytest.raises(IntegrityError):
            TenantMembership.objects.create(
                tenant=self.tenant,
                user_id=self.user_id,
            )

    def test_same_user_can_belong_to_different_tenants(self):
        tenant_b = Tenant.objects.create(
            name="Globex Corporation",
            slug="globex",
        )

        membership_a = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        membership_b = TenantMembership.objects.create(
            tenant=tenant_b,
            user_id=self.user_id,
        )

        assert membership_a.id != membership_b.id

    def test_invited_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.INVITED,
        )

        assert membership.status == (
            TenantMembership.Status.INVITED
        )

    def test_string_representation(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        assert str(self.user_id) in str(membership)
        assert "Acme Corporation" in str(membership)