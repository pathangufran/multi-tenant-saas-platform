import uuid
import pytest
from apps.tenants.audit_selectors import (
    AuditEventSelector,
)
from apps.tenants.audit_service import (
    AuditEventService,
)
from apps.tenants.models import (
    Tenant,TenantMembership,AuditEvent
)
from apps.tenants.services import TenantService

@pytest.mark.django_db
class TestAuditEventService:

    def test_record_creates_audit_event(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        event = AuditEventService.record(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_CREATED
            ),
            entity_type="tenant",
            entity_id=tenant_id,
            metadata={
                "name": "Test Tenant",
            },
        )

        assert event.id is not None
        assert event.tenant_id == tenant_id
        assert event.actor_user_id == user_id

        assert (
            event.event_type
            == AuditEvent.EventType.TENANT_CREATED
        )

        assert event.entity_type == "tenant"
        assert event.entity_id == tenant_id

        assert event.metadata == {
            "name": "Test Tenant",
        }

    def test_record_tenant_event(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        event = (
            AuditEventService.record_tenant_event(
                tenant_id=tenant_id,
                actor_user_id=user_id,
                event_type=(
                    AuditEvent.EventType.TENANT_SUSPENDED
                ),
            )
        )

        assert event.tenant_id == tenant_id
        assert event.actor_user_id == user_id
        assert event.entity_type == "tenant"
        assert event.entity_id == tenant_id
        assert event.metadata == {}

@pytest.mark.django_db
class TestAuditEventSelectors:

    def test_get_by_id(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        event = AuditEvent.objects.create(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_CREATED
            ),
            entity_type="tenant",
            entity_id=tenant_id,
        )

        result = AuditEventSelector.get_by_id(
            event_id=event.id
        )

        assert result.id == event.id

    def test_get_for_tenant(self):
        tenant_one = uuid.uuid4()
        tenant_two = uuid.uuid4()
        user_id = uuid.uuid4()

        event_one = AuditEvent.objects.create(
            tenant_id=tenant_one,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_CREATED
            ),
            entity_type="tenant",
            entity_id=tenant_one,
        )

        AuditEvent.objects.create(
            tenant_id=tenant_two,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_CREATED
            ),
            entity_type="tenant",
            entity_id=tenant_two,
        )

        events = AuditEventSelector.get_for_tenant(
            tenant_id=tenant_one
        )

        assert list(events) == [event_one]

    def test_get_for_tenant_and_event_type(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        created_event = AuditEvent.objects.create(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_CREATED
            ),
            entity_type="tenant",
            entity_id=tenant_id,
        )

        AuditEvent.objects.create(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_UPDATED
            ),
            entity_type="tenant",
            entity_id=tenant_id,
        )

        events = (
            AuditEventSelector
            .get_for_tenant_and_event_type(
                tenant_id=tenant_id,
                event_type=(
                    AuditEvent.EventType.TENANT_CREATED
                ),
            )
        )

        assert list(events) == [created_event]

@pytest.mark.django_db
class TestTenantAuditIntegration:

    def test_create_tenant_creates_audit_event(self):
        user_id = uuid.uuid4()

        tenant = TenantService.create_tenant(
            name="Test Tenant",
            slug="test-tenant",
            owner_user_id=user_id,
        )

        event = AuditEvent.objects.get(
            tenant_id=tenant.id,
            event_type=(
                AuditEvent.EventType.TENANT_CREATED
            ),
        )

        assert event.actor_user_id == user_id
        assert event.entity_type == "tenant"
        assert event.entity_id == tenant.id

        assert event.metadata["name"] == (
            "Test Tenant"
        )

        assert event.metadata["slug"] == (
            "test-tenant"
        )

    def test_update_tenant_creates_audit_event(self):
        user_id = uuid.uuid4()

        tenant = Tenant.objects.create(
            name="Original Tenant",
            slug="original-tenant",
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        TenantService.update_tenant(
            tenant_id=tenant.id,
            user_id=user_id,
            name="Updated Tenant",
            slug="updated-tenant",
        )

        event = AuditEvent.objects.get(
            tenant_id=tenant.id,
            event_type=(
                AuditEvent.EventType.TENANT_UPDATED
            ),
        )

        assert event.actor_user_id == user_id

        assert (
            event.metadata["previous_name"]
            == "Original Tenant"
        )

        assert (
            event.metadata["new_name"]
            == "Updated Tenant"
        )

        assert (
            event.metadata["previous_slug"]
            == "original-tenant"
        )

        assert (
            event.metadata["new_slug"]
            == "updated-tenant"
        )

    def test_suspend_tenant_creates_audit_event(self):
        user_id = uuid.uuid4()

        tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        TenantService.suspend_tenant(
            tenant_id=tenant.id,
            user_id=user_id,
        )

        event = AuditEvent.objects.get(
            tenant_id=tenant.id,
            event_type=(
                AuditEvent.EventType.TENANT_SUSPENDED
            ),
        )

        assert event.actor_user_id == user_id

        assert (
            event.metadata["previous_status"]
            == Tenant.Status.ACTIVE
        )

        assert (
            event.metadata["new_status"]
            == Tenant.Status.SUSPENDED
        )

    def test_activate_tenant_creates_audit_event(self):
        user_id = uuid.uuid4()

        tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            status=Tenant.Status.SUSPENDED,
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        TenantService.activate_tenant(
            tenant_id=tenant.id,
            user_id=user_id,
        )

        event = AuditEvent.objects.get(
            tenant_id=tenant.id,
            event_type=(
                AuditEvent.EventType.TENANT_ACTIVATED
            ),
        )

        assert event.actor_user_id == user_id

        assert (
            event.metadata["previous_status"]
            == Tenant.Status.SUSPENDED
        )

        assert (
            event.metadata["new_status"]
            == Tenant.Status.ACTIVE
        )

    def test_deactivate_tenant_creates_audit_event(
        self,
    ):
        user_id = uuid.uuid4()

        tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        TenantService.deactivate_tenant(
            tenant_id=tenant.id,
            user_id=user_id,
        )

        event = AuditEvent.objects.get(
            tenant_id=tenant.id,
            event_type=(
                AuditEvent.EventType.TENANT_DEACTIVATED
            ),
        )

        assert event.actor_user_id == user_id

        assert (
            event.metadata["previous_status"]
            == Tenant.Status.ACTIVE
        )

        assert (
            event.metadata["new_status"]
            == Tenant.Status.DEACTIVATED
        )