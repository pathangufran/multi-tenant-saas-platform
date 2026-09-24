import uuid
import pytest
from apps.common.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)
from apps.tenants.models import (
    Tenant, TenantMembership, Role
)
from apps.tenants.rbac_service import (
    RBACService,
    TenantRoleService,
)
from apps.tenants.membership_service import (
    TenantMembershipRoleService,
)

@pytest.mark.django_db
class TestMembershipRoleManagement:

    def setup_method(self):
        RBACService.initialize_permissions()

        self.tenant = Tenant.objects.create(
            name="Tenant A",
            slug=f"tenant-a-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        self.other_tenant = Tenant.objects.create(
            name="Tenant B",
            slug=f"tenant-b-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        self.user_id = uuid.uuid4()
        self.other_user_id = uuid.uuid4()

        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        self.other_membership = (
            TenantMembership.objects.create(
                tenant=self.other_tenant,
                user_id=self.other_user_id,
                status=TenantMembership.Status.ACTIVE,
            )
        )

        self.owner_role = Role.objects.get(
            code="OWNER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        self.viewer_role = Role.objects.get(
            code="VIEWER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        self.custom_role = (
            TenantRoleService.create_role(
                tenant_id=self.tenant.id,
                name="Project Manager",
                code="PROJECT_MANAGER",
                permission_codes=[
                    "projects.read",
                    "projects.create",
                    "projects.update",
                ],
            )
        )

        self.other_tenant_role = (
            TenantRoleService.create_role(
                tenant_id=self.other_tenant.id,
                name="Other Role",
                code="OTHER_ROLE",
            )
        )

        self.platform_role = Role.objects.create(
            name="Platform Support",
            code="PLATFORM_SUPPORT",
            scope=Role.Scope.PLATFORM,
            tenant=None,
            is_system_role=True,
        )

    def test_assign_system_role(self):
        membership = (
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.owner_role.id,
            )
        )

        assert membership.role_id == self.owner_role.id

    def test_assign_system_viewer_role(self):
        membership = (
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.viewer_role.id,
            )
        )

        assert membership.role_id == self.viewer_role.id

    def test_assign_custom_tenant_role(self):
        membership = (
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.custom_role.id,
            )
        )

        assert membership.role_id == self.custom_role.id

    def test_change_role(self):
        TenantMembershipRoleService.assign_role(
            tenant_id=self.tenant.id,
            membership_id=self.membership.id,
            role_id=self.viewer_role.id,
        )

        membership = (
            TenantMembershipRoleService.change_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.custom_role.id,
            )
        )

        assert membership.role_id == self.custom_role.id

    def test_remove_role(self):
        TenantMembershipRoleService.assign_role(
            tenant_id=self.tenant.id,
            membership_id=self.membership.id,
            role_id=self.custom_role.id,
        )

        membership = (
            TenantMembershipRoleService.remove_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
            )
        )

        assert membership.role_id is None

    def test_get_membership_role(self):
        TenantMembershipRoleService.assign_role(
            tenant_id=self.tenant.id,
            membership_id=self.membership.id,
            role_id=self.viewer_role.id,
        )

        role = (
            TenantMembershipRoleService.get_membership_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
            )
        )

        assert role.id == self.viewer_role.id

    def test_membership_without_role_returns_none(self):
        role = (
            TenantMembershipRoleService.get_membership_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
            )
        )

        assert role is None

    def test_other_tenant_role_cannot_be_assigned(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.other_tenant_role.id,
            )

        self.membership.refresh_from_db()

        assert self.membership.role_id is None

    def test_other_tenant_membership_cannot_be_modified(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.other_membership.id,
                role_id=self.viewer_role.id,
            )

        self.other_membership.refresh_from_db()

        assert self.other_membership.role_id is None

    def test_platform_role_cannot_be_assigned(self):
        with pytest.raises(ValidationError):
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.platform_role.id,
            )

        self.membership.refresh_from_db()

        assert self.membership.role_id is None

    def test_unknown_role_is_rejected(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=uuid.uuid4(),
            )

    def test_unknown_membership_is_rejected(self):
        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=uuid.uuid4(),
                role_id=self.viewer_role.id,
            )

    def test_removed_membership_cannot_receive_role(self):
        self.membership.status = (
            TenantMembership.Status.REMOVED
        )

        self.membership.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        with pytest.raises(ValidationError):
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.viewer_role.id,
            )

    def test_suspended_membership_can_be_prevented_or_allowed_consistently(self):
        self.membership.status = (
            TenantMembership.Status.SUSPENDED
        )

        self.membership.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        membership = (
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.viewer_role.id,
            )
        )

        assert membership.role_id == self.viewer_role.id

    def test_role_change_is_tenant_scoped(self):
        TenantMembershipRoleService.assign_role(
            tenant_id=self.tenant.id,
            membership_id=self.membership.id,
            role_id=self.custom_role.id,
        )

        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.change_role(
                tenant_id=self.other_tenant.id,
                membership_id=self.membership.id,
                role_id=self.viewer_role.id,
            )

        self.membership.refresh_from_db()

        assert self.membership.role_id == self.custom_role.id

    def test_remove_role_is_tenant_scoped(self):
        TenantMembershipRoleService.assign_role(
            tenant_id=self.tenant.id,
            membership_id=self.membership.id,
            role_id=self.custom_role.id,
        )

        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.remove_role(
                tenant_id=self.other_tenant.id,
                membership_id=self.membership.id,
            )

        self.membership.refresh_from_db()

        assert self.membership.role_id == self.custom_role.id

    def test_get_role_is_tenant_scoped(self):
        TenantMembershipRoleService.assign_role(
            tenant_id=self.tenant.id,
            membership_id=self.membership.id,
            role_id=self.custom_role.id,
        )

        with pytest.raises(ResourceNotFoundError):
            TenantMembershipRoleService.get_membership_role(
                tenant_id=self.other_tenant.id,
                membership_id=self.membership.id,
            )

    def test_role_assignment_is_idempotent(self):
        first = (
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.viewer_role.id,
            )
        )

        second = (
            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.viewer_role.id,
            )
        )

        assert first.role_id == self.viewer_role.id
        assert second.role_id == self.viewer_role.id

        self.membership.refresh_from_db()

        assert self.membership.role_id == self.viewer_role.id