import uuid
import pytest
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from apps.outbox.models import OutboxEvent
from apps.tenants.context import (
    clear_tenant_context,
    set_tenant_context,
)
from apps.tenants.isolation import TenantIsolationService
from apps.tenants.membership_service import (
    TenantMembershipService,
)
from apps.tenants.models import (
    Role,
    Tenant,
    TenantMembership,
)
from apps.tenants.tenant_context import TenantContext

@pytest.mark.django_db
class TestTenantMembershipService:

    def setup_method(self):
        self.user_id = uuid.uuid4()

        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug=f"acme-{uuid.uuid4().hex[:8]}",
        )

        self.context_token = set_tenant_context(
            TenantContext(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
            )
        )

        self.role = Role.objects.create(
            name="Member",
            code=f"member-{uuid.uuid4().hex[:8]}",
            scope=Role.Scope.TENANT,
            tenant=self.tenant,
        )

    def teardown_method(self):
        clear_tenant_context(self.context_token)

    def test_create_membership(self):
        membership = TenantMembershipService.create_membership(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            role=self.role,
        )

        assert membership.tenant_id == self.tenant.id
        assert membership.user_id == self.user_id
        assert membership.role_id == self.role.id
        assert membership.status == TenantMembership.Status.ACTIVE
        assert membership.joined_at is not None

        event = OutboxEvent.objects.get(
            event_type="member.joined",
            aggregate_id=str(membership.id),
        )

        assert event.aggregate_type == "membership"
        assert event.aggregate_version == 1
        assert event.tenant_id == self.tenant.id
        assert event.data["membership_id"] == str(membership.id)

    def test_create_invited_membership(self):
        membership = TenantMembershipService.create_membership(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            role=self.role,
            status=TenantMembership.Status.INVITED,
        )

        assert membership.status == TenantMembership.Status.INVITED
        assert membership.joined_at is None

        event = OutboxEvent.objects.get(
            event_type="member.invited",
            aggregate_id=str(membership.id),
        )

        assert event.aggregate_version == 1
        assert event.data["user_id"] == str(self.user_id)
        assert event.data["role_id"] == str(self.role.id)

    def test_duplicate_membership_raises_conflict(self):
        TenantMembershipService.create_membership(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            role=self.role,
        )

        with pytest.raises(
            ConflictError,
            match="already a member",
        ):
            TenantMembershipService.create_membership(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                role=self.role,
            )

        assert OutboxEvent.objects.filter(
            event_type="member.joined",
        ).count() == 1

    def test_unknown_tenant_raises_not_found(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipService.create_membership(
                tenant_id=uuid.uuid4(),
                user_id=self.user_id,
                role=self.role,
            )

        assert OutboxEvent.objects.count() == 0

    def test_create_membership_does_not_require_auth_database(self):
        random_user_id = uuid.uuid4()

        membership = TenantMembershipService.create_membership(
            tenant_id=self.tenant.id,
            user_id=random_user_id,
            role=self.role,
        )

        assert membership.user_id == random_user_id

    def test_activate_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        result = TenantMembershipService.activate_membership(
            membership_id=membership.id,
            tenant_id=self.tenant.id,
        )

        assert result.status == TenantMembership.Status.ACTIVE
        assert result.joined_at is not None

        # Already-active membership must not generate another event.
        assert OutboxEvent.objects.filter(
            aggregate_id=str(membership.id),
        ).count() == 0

    def test_activate_invited_membership_emits_member_joined(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            role=self.role,
            status=TenantMembership.Status.INVITED,
        )

        result = TenantMembershipService.activate_membership(
            membership_id=membership.id,
            tenant_id=self.tenant.id,
        )

        assert result.status == TenantMembership.Status.ACTIVE
        assert result.joined_at is not None

        event = OutboxEvent.objects.get(
            event_type="member.joined",
            aggregate_id=str(membership.id),
        )

        assert event.aggregate_version == 2
        assert event.data["membership_id"] == str(membership.id)

    def test_reactivating_suspended_membership_does_not_emit_joined(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            role=self.role,
            status=TenantMembership.Status.SUSPENDED,
        )

        result = TenantMembershipService.activate_membership(
            membership_id=membership.id,
            tenant_id=self.tenant.id,
        )

        assert result.status == TenantMembership.Status.ACTIVE

        assert not OutboxEvent.objects.filter(
            event_type="member.joined",
            aggregate_id=str(membership.id),
        ).exists()

    def test_suspend_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        result = TenantMembershipService.suspend_membership(
            membership_id=membership.id,
            tenant_id=self.tenant.id,
        )

        assert result.status == TenantMembership.Status.SUSPENDED

    def test_remove_membership(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
        )

        result = TenantMembershipService.remove_membership(
            membership_id=membership.id,
            tenant_id=self.tenant.id,
        )

        assert result.status == TenantMembership.Status.REMOVED

    def test_removed_membership_cannot_be_activated(self):
        membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.REMOVED,
        )

        with pytest.raises(ConflictError):
            TenantMembershipService.activate_membership(
                membership_id=membership.id,
                tenant_id=self.tenant.id,
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
                tenant_id=self.tenant.id,
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
                tenant_id=self.tenant.id,
            )
