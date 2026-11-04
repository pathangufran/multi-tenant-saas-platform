import uuid
import pytest
from apps.common.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)
from apps.tenants.models import (
    Tenant, TenantMembership,Permission,
    Role,PlatformRoleAssignment
)
from apps.tenants.rbac_service import (
    PlatformRoleService,
    RBACService,
)

@pytest.mark.django_db
class TestPlatformRoles:

    def setup_method(self):
        RBACService.initialize_permissions()
        RBACService.initialize_tenant_roles()
        PlatformRoleService.initialize_platform_roles()

        self.tenant = Tenant.objects.create(
            name="Tenant A",
            slug=f"tenant-a-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        self.user_id = uuid.uuid4()

        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        self.super_admin = (
            PlatformRoleService.get_platform_role_by_code(
                code="SUPER_ADMIN",
            )
        )

        self.support = (
            PlatformRoleService.get_platform_role_by_code(
                code="SUPPORT",
            )
        )

        self.operations = (
            PlatformRoleService.get_platform_role_by_code(
                code="OPERATIONS",
            )
        )

    def test_initialize_platform_roles(self):
        roles = Role.objects.filter(
            scope=Role.Scope.PLATFORM,
        )

        role_codes = set(
            roles.values_list(
                "code",
                flat=True,
            )
        )

        assert role_codes == {
            "SUPER_ADMIN",
            "SUPPORT",
            "OPERATIONS",
        }

    def test_platform_roles_have_no_tenant(self):
        roles = Role.objects.filter(
            scope=Role.Scope.PLATFORM,
        )

        assert roles.exists()

        assert not roles.filter(
            tenant__isnull=False,
        ).exists()

    def test_platform_roles_are_system_roles(self):
        roles = Role.objects.filter(
            scope=Role.Scope.PLATFORM,
        )

        assert roles.exists()

        assert not roles.filter(
            is_system_role=False,
        ).exists()

    def test_super_admin_has_all_permissions(self):
        permission_codes = set(
            self.super_admin.permissions.values_list(
                "code",
                flat=True,
            )
        )

        expected = set(
            self.super_admin.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == expected

        assert (
            "projects.create"
            in permission_codes
        )

        assert (
            "billing.manage"
            in permission_codes
        )

    def test_support_has_read_permissions(self):
        permission_codes = set(
            self.support.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert "tenant.read" in permission_codes
        assert "users.read" in permission_codes
        assert "projects.read" in permission_codes
        assert "tasks.read" in permission_codes
        assert "billing.read" in permission_codes

    def test_support_does_not_have_billing_manage(self):
        assert not self.support.permissions.filter(
            code="billing.manage",
        ).exists()

    def test_get_platform_role(self):
        role = PlatformRoleService.get_platform_role(
            role_id=self.super_admin.id,
        )

        assert role.id == self.super_admin.id
        assert role.scope == Role.Scope.PLATFORM
        assert role.tenant_id is None

    def test_get_platform_role_rejects_tenant_role(self):
        tenant_role = Role.objects.get(
            code="OWNER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        with pytest.raises(ResourceNotFoundError):
            PlatformRoleService.get_platform_role(
                role_id=tenant_role.id,
            )

    def test_get_platform_role_by_code(self):
        role = (
            PlatformRoleService.get_platform_role_by_code(
                code="SUPER_ADMIN",
            )
        )

        assert role.id == self.super_admin.id

    def test_get_unknown_platform_role_fails(self):
        with pytest.raises(ResourceNotFoundError):
            PlatformRoleService.get_platform_role_by_code(
                code="DOES_NOT_EXIST",
            )

    def test_assign_platform_role(self):
        assignment = (
            PlatformRoleService.assign_role(
                user_id=self.user_id,
                role_id=self.super_admin.id,
            )
        )

        assert assignment.user_id == self.user_id
        assert assignment.role_id == self.super_admin.id

        assert PlatformRoleAssignment.objects.filter(
            user_id=self.user_id,
            role=self.super_admin,
        ).exists()

    def test_assign_platform_role_is_idempotent(self):
        first = PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        second = PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert first.id == second.id

        assert PlatformRoleAssignment.objects.filter(
            user_id=self.user_id,
            role=self.support,
        ).count() == 1

    def test_assign_multiple_platform_roles(self):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.super_admin.id,
        )

        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert (
            PlatformRoleAssignment.objects.filter(
                user_id=self.user_id,
            ).count()
            == 2
        )

    def test_tenant_role_cannot_be_assigned_as_platform_role(
        self,
    ):
        tenant_role = Role.objects.get(
            code="OWNER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        with pytest.raises(ResourceNotFoundError):
            PlatformRoleService.assign_role(
                user_id=self.user_id,
                role_id=tenant_role.id,
            )

    def test_remove_platform_role(self):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        removed = PlatformRoleService.remove_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert removed is True

        assert not PlatformRoleAssignment.objects.filter(
            user_id=self.user_id,
            role=self.support,
        ).exists()

    def test_remove_missing_platform_role_is_idempotent(self):
        removed = PlatformRoleService.remove_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert removed is False

    def test_has_role_returns_true(self):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert PlatformRoleService.has_role(
            user_id=self.user_id,
            role_code="SUPPORT",
        ) is True

    def test_has_role_returns_false(self):
        assert PlatformRoleService.has_role(
            user_id=self.user_id,
            role_code="SUPPORT",
        ) is False

    def test_has_permission_from_platform_role(self):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert PlatformRoleService.has_permission(
            user_id=self.user_id,
            permission_code="projects.read",
        ) is True

    def test_platform_permission_is_not_granted_without_role(
        self,
    ):
        assert PlatformRoleService.has_permission(
            user_id=self.user_id,
            permission_code="projects.read",
        ) is False

    def test_support_does_not_have_write_permission(self):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        assert PlatformRoleService.has_permission(
            user_id=self.user_id,
            permission_code="projects.create",
        ) is False

    def test_get_user_platform_roles(self):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.operations.id,
        )

        roles = list(
            PlatformRoleService.get_user_roles(
                user_id=self.user_id,
            )
        )

        role_codes = {
            role.code
            for role in roles
        }

        assert role_codes == {
            "SUPPORT",
            "OPERATIONS",
        }

    def test_platform_role_is_independent_of_tenant_membership(
        self,
    ):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        self.membership.delete()

        assert PlatformRoleService.has_role(
            user_id=self.user_id,
            role_code="SUPPORT",
        ) is True

    def test_platform_role_does_not_modify_tenant_membership(
        self,
    ):
        PlatformRoleService.assign_role(
            user_id=self.user_id,
            role_id=self.support.id,
        )

        self.membership.refresh_from_db()

        assert self.membership.role_id is None

    def test_platform_role_cannot_be_used_as_tenant_membership_role(
        self,
    ):
        with pytest.raises(ValidationError):
            from apps.tenants.membership_service import (
                TenantMembershipRoleService,
            )

            TenantMembershipRoleService.assign_role(
                tenant_id=self.tenant.id,
                membership_id=self.membership.id,
                role_id=self.support.id,
            )

        self.membership.refresh_from_db()

        assert self.membership.role_id is None