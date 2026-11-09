import uuid
from unittest.mock import patch
import pytest
from apps.outbox.models import OutboxEvent
from apps.tenants.models import (
    AuditEvent,
    Tenant,
    TenantMembership,
)
from apps.tenants.services import TenantService

@pytest.mark.django_db
class TestTenantService:

    def setup_method(self):
        self.owner_user_id = uuid.uuid4()

    def test_create_tenant(self):
        tenant = TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        assert tenant.name == "Acme Corporation"
        assert tenant.slug == "acme"
        assert tenant.status == Tenant.Status.ACTIVE

    def test_create_tenant_creates_owner_membership(self):
        tenant = TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        membership = TenantMembership.objects.get(
            tenant=tenant,
            user_id=self.owner_user_id,
        )

        assert membership.status == TenantMembership.Status.ACTIVE
        assert membership.joined_at is not None

    def test_create_tenant_emits_tenant_created_event(self):
        tenant = TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        event = OutboxEvent.objects.get(
            event_type="tenant.created",
            aggregate_type="tenant",
            aggregate_id=str(tenant.id),
        )

        assert event.tenant_id == tenant.id
        assert event.aggregate_version == 1
        assert event.data["tenant_id"] == str(tenant.id)
        assert event.data["owner_user_id"] == str(self.owner_user_id)

    def test_create_tenant_emits_owner_member_joined_event(self):
        tenant = TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        membership = TenantMembership.objects.get(
            tenant=tenant,
            user_id=self.owner_user_id,
        )

        event = OutboxEvent.objects.get(
            event_type="member.joined",
            aggregate_type="membership",
            aggregate_id=str(membership.id),
        )

        assert event.tenant_id == tenant.id
        assert event.aggregate_version == 1
        assert event.data["user_id"] == str(self.owner_user_id)

    def test_create_tenant_creates_two_outbox_events(self):
        TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        assert OutboxEvent.objects.count() == 2

        assert OutboxEvent.objects.filter(
            event_type="tenant.created",
        ).count() == 1

        assert OutboxEvent.objects.filter(
            event_type="member.joined",
        ).count() == 1

    def test_create_tenant_strips_name(self):
        tenant = TenantService.create_tenant(
            name="  Acme Corporation  ",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        assert tenant.name == "Acme Corporation"

    def test_create_tenant_normalizes_slug(self):
        tenant = TenantService.create_tenant(
            name="Acme Corporation",
            slug="Acme Corporation",
            owner_user_id=self.owner_user_id,
        )

        assert tenant.slug == "acme-corporation"

    def test_duplicate_slug_is_rejected(self):
        TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        with pytest.raises(ValueError, match="already exists"):
            TenantService.create_tenant(
                name="Another Acme",
                slug="ACME",
                owner_user_id=uuid.uuid4(),
            )

        assert Tenant.objects.count() == 1
        assert OutboxEvent.objects.count() == 2

    def test_empty_name_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="Tenant name is required",
        ):
            TenantService.create_tenant(
                name="   ",
                slug="acme",
                owner_user_id=self.owner_user_id,
            )

        assert Tenant.objects.count() == 0
        assert OutboxEvent.objects.count() == 0

    def test_empty_slug_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="Tenant slug is required",
        ):
            TenantService.create_tenant(
                name="Acme Corporation",
                slug="---",
                owner_user_id=self.owner_user_id,
            )

        assert Tenant.objects.count() == 0
        assert OutboxEvent.objects.count() == 0

    def test_created_tenant_is_persisted(self):
        tenant = TenantService.create_tenant(
            name="Acme Corporation",
            slug="acme",
            owner_user_id=self.owner_user_id,
        )

        assert Tenant.objects.filter(
            id=tenant.id,
        ).exists()

    def test_outbox_failure_rolls_back_tenant_and_membership(self):
        with patch(
            "apps.tenants.services.OutboxService.record_event",
            side_effect=RuntimeError("outbox failure"),
        ):
            with pytest.raises(
                RuntimeError,
                match="outbox failure",
            ):
                TenantService.create_tenant(
                    name="Acme Corporation",
                    slug="acme",
                    owner_user_id=self.owner_user_id,
                )

        assert Tenant.objects.count() == 0
        assert TenantMembership.objects.count() == 0
        assert AuditEvent.objects.count() == 0
        assert OutboxEvent.objects.count() == 0
