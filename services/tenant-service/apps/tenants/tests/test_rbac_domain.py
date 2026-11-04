import uuid
import pytest
from apps.tenants.models import (
    Role,
    Tenant,
    Permission,
    TenantMembership,
)
from apps.tenants.rbac_service import (
    RBACService,
)

@pytest.mark.django_db
class TestPermissionModel:

    def test_permission_can_be_created(self):
        permission = Permission.objects.create(
            code="test.read",
            name="Test Read",
            description="Test permission.",
        )

        assert permission.id is not None
        assert permission.code == "test.read"
        assert permission.name == "Test Read"

    def test_permission_code_is_unique(self):
        Permission.objects.create(
            code="test.read",
            name="Test Read",
        )

        with pytest.raises(Exception):
            Permission.objects.create(
                code="test.read",
                name="Duplicate",
            )

@pytest.mark.django_db
class TestRoleModel:

    def test_tenant_role_requires_tenant(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        role = Role.objects.create(
            name="Custom Role",
            code="CUSTOM",
            scope=Role.Scope.TENANT,
            tenant=tenant,
        )

        assert role.tenant_id == tenant.id
        assert role.scope == Role.Scope.TENANT

    def test_platform_role_has_no_tenant(self):
        role = Role.objects.create(
            name="Support",
            code="SUPPORT",
            scope=Role.Scope.PLATFORM,
        )

        assert role.tenant_id is None
        assert role.scope == Role.Scope.PLATFORM

    def test_role_can_have_permissions(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        role = Role.objects.create(
            name="Manager",
            code="MANAGER",
            scope=Role.Scope.TENANT,
            tenant=tenant,
        )

        permission = Permission.objects.create(
            code="projects.read",
            name="Read Projects",
        )

        role.permissions.add(permission)

        assert role.permissions.count() == 1
        assert (
            role.permissions.first().code
            == "projects.read"
        )

@pytest.mark.django_db
class TestRBACInitialization:

    def test_initialize_permissions(self):
        permissions = (
            RBACService.initialize_permissions()
        )

        assert len(permissions) == 16

        assert Permission.objects.filter(
            code="tenant.read"
        ).exists()

        assert Permission.objects.filter(
            code="projects.create"
        ).exists()

        assert Permission.objects.filter(
            code="billing.manage"
        ).exists()

    def test_initialize_permissions_is_idempotent(self):
        first = (
            RBACService.initialize_permissions()
        )

        second = (
            RBACService.initialize_permissions()
        )

        assert len(first) == len(second)

        assert Permission.objects.count() == 16

    def test_initialize_tenant_roles(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        roles = RBACService.initialize_tenant_roles(
            tenant=tenant
        )

        assert len(roles) == 5

        role_codes = set(
            Role.objects.filter(
                tenant=tenant,
                scope=Role.Scope.TENANT,
                is_system_role=True,
            ).values_list(
                "code",
                flat=True,
            )
        )

        assert role_codes == {
            "OWNER",
            "ADMIN",
            "MANAGER",
            "MEMBER",
            "VIEWER",
        }

    def test_owner_has_full_tenant_permissions(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        RBACService.initialize_tenant_roles(
            tenant=tenant
        )

        owner = Role.objects.get(
            tenant=tenant,
            code="OWNER",
            scope=Role.Scope.TENANT,
        )

        permission_codes = set(
            owner.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "tenant.read",
            "tenant.update",
            "users.read",
            "users.create",
            "users.update",
            "users.delete",
            "projects.read",
            "projects.create",
            "projects.update",
            "projects.delete",
            "tasks.read",
            "tasks.create",
            "tasks.update",
            "tasks.delete",
            "billing.read",
            "billing.manage",
        }

    def test_viewer_has_read_permissions(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        RBACService.initialize_tenant_roles(
            tenant=tenant
        )

        viewer = Role.objects.get(
            tenant=tenant,
            code="VIEWER",
            scope=Role.Scope.TENANT,
        )

        permission_codes = set(
            viewer.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "tenant.read",
            "projects.read",
            "tasks.read",
        }

@pytest.mark.django_db
class TestMembershipRoles:

    def test_membership_can_have_role(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        role = Role.objects.create(
            name="Manager",
            code="MANAGER",
            scope=Role.Scope.TENANT,
            tenant=tenant,
        )

        membership = TenantMembership.objects.create(
            tenant=tenant,
            user_id=uuid.uuid4(),
            role=role,
            status=TenantMembership.Status.ACTIVE,
        )

        assert membership.role_id == role.id
        assert membership.role.code == "MANAGER"

    def test_assign_role_to_membership(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        role = Role.objects.create(
            name="Manager",
            code="MANAGER",
            scope=Role.Scope.TENANT,
            tenant=tenant,
        )

        membership = (
            TenantMembership.objects.create(
                tenant=tenant,
                user_id=uuid.uuid4(),
                status=(
                    TenantMembership.Status.ACTIVE
                ),
            )
        )

        RBACService.assign_role_to_membership(
            membership=membership,
            role=role,
        )

        membership.refresh_from_db()

        assert membership.role_id == role.id

    def test_platform_role_cannot_be_assigned_to_membership(
        self,
    ):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        platform_role = Role.objects.create(
            name="Support",
            code="SUPPORT",
            scope=Role.Scope.PLATFORM,
        )

        membership = (
            TenantMembership.objects.create(
                tenant=tenant,
                user_id=uuid.uuid4(),
                status=(
                    TenantMembership.Status.ACTIVE
                ),
            )
        )

        with pytest.raises(ValueError):
            RBACService.assign_role_to_membership(
                membership=membership,
                role=platform_role,
            )

        membership.refresh_from_db()

        assert membership.role is None

    def test_role_from_different_tenant_cannot_be_assigned(
        self,
    ):
        tenant_one = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        tenant_two = Tenant.objects.create(
            name="Tenant Two",
            slug="tenant-two",
        )

        role = Role.objects.create(
            name="Custom Manager",
            code="CUSTOM_MANAGER",
            scope=Role.Scope.TENANT,
            tenant=tenant_two,
        )

        membership = (
            TenantMembership.objects.create(
                tenant=tenant_one,
                user_id=uuid.uuid4(),
                status=(
                    TenantMembership.Status.ACTIVE
                ),
            )
        )

        with pytest.raises(ValueError):
            RBACService.assign_role_to_membership(
                membership=membership,
                role=role,
            )

        membership.refresh_from_db()

        assert membership.role is None

    def test_system_role_can_be_assigned_to_membership(self):
        tenant = Tenant.objects.create(
            name="Tenant One",
            slug="tenant-one",
        )

        role = Role.objects.create(
            name="Admin",
            code="ADMIN",
            scope=Role.Scope.TENANT,
            tenant=tenant,
            is_system_role=True,
        )

        membership = TenantMembership.objects.create(
            tenant=tenant,
            user_id=uuid.uuid4(),
            status=TenantMembership.Status.ACTIVE,
        )

        RBACService.assign_role_to_membership(
            membership=membership,
            role=role,
        )

        membership.refresh_from_db()

        assert membership.role_id == role.id