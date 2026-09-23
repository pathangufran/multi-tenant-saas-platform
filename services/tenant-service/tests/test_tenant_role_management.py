import uuid
import pytest
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from apps.tenants.models import (
    Tenant,Permission, Role
)
from apps.tenants.rbac_service import (
    RBACService,
    TenantRoleService,
)

@pytest.mark.django_db
class TestTenantRoleManagement:

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

    def test_list_roles_returns_system_roles(self):
        roles = list(
            TenantRoleService.list_roles(
                tenant_id=self.tenant.id,
            )
        )

        role_codes = {
            role.code
            for role in roles
        }

        assert {
            "OWNER",
            "ADMIN",
            "MANAGER",
            "MEMBER",
            "VIEWER",
        }.issubset(role_codes)

    def test_list_roles_returns_custom_roles(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Accountant",
            code="ACCOUNTANT",
            description="Handles financial operations.",
        )

        roles = list(
            TenantRoleService.list_roles(
                tenant_id=self.tenant.id,
            )
        )

        role_ids = {
            current_role.id
            for current_role in roles
        }

        assert role.id in role_ids

    def test_list_roles_does_not_return_other_tenant_roles(self):
        other_role = TenantRoleService.create_role(
            tenant_id=self.other_tenant.id,
            name="Support Agent",
            code="SUPPORT_AGENT",
        )

        roles = list(
            TenantRoleService.list_roles(
                tenant_id=self.tenant.id,
            )
        )

        role_ids = {
            role.id
            for role in roles
        }

        assert other_role.id not in role_ids

    def test_create_custom_role(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Project Manager",
            code="PROJECT_MANAGER",
            description="Manages project operations.",
        )

        assert role.tenant_id == self.tenant.id
        assert role.name == "Project Manager"
        assert role.code == "PROJECT_MANAGER"
        assert role.scope == Role.Scope.TENANT
        assert role.is_system_role is False

    def test_create_role_normalizes_code(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Project Manager",
            code=" project_manager ",
        )

        assert role.code == "PROJECT_MANAGER"

    def test_create_role_assigns_permissions(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Project Manager",
            code="PROJECT_MANAGER",
            permission_codes=[
                "projects.read",
                "projects.create",
                "projects.update",
            ],
        )

        permission_codes = set(
            role.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "projects.read",
            "projects.create",
            "projects.update",
        }

    def test_create_role_rejects_duplicate_code(self):
        TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Project Manager",
            code="PROJECT_MANAGER",
        )

        with pytest.raises(ConflictError):
            TenantRoleService.create_role(
                tenant_id=self.tenant.id,
                name="Another Project Manager",
                code="PROJECT_MANAGER",
            )

    def test_same_role_code_allowed_for_different_tenants(self):
        role_a = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Support",
            code="SUPPORT",
        )

        role_b = TenantRoleService.create_role(
            tenant_id=self.other_tenant.id,
            name="Support",
            code="SUPPORT",
        )

        assert role_a.id != role_b.id
        assert role_a.tenant_id != role_b.tenant_id

    def test_create_role_rejects_unknown_permission(self):
        with pytest.raises(ValidationError):
            TenantRoleService.create_role(
                tenant_id=self.tenant.id,
                name="Invalid Role",
                code="INVALID_ROLE",
                permission_codes=[
                    "permission.does.not.exist",
                ],
            )

    def test_create_role_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            TenantRoleService.create_role(
                tenant_id=self.tenant.id,
                name="   ",
                code="INVALID_ROLE",
            )

    def test_create_role_rejects_empty_code(self):
        with pytest.raises(ValidationError):
            TenantRoleService.create_role(
                tenant_id=self.tenant.id,
                name="Invalid Role",
                code="   ",
            )

    def test_update_custom_role(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Old Name",
            code="CUSTOM_ROLE",
        )

        updated = TenantRoleService.update_role(
            tenant_id=self.tenant.id,
            role_id=role.id,
            name="Updated Name",
            description="Updated description.",
        )

        assert updated.name == "Updated Name"
        assert updated.description == (
            "Updated description."
        )

    def test_update_custom_role_permissions(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Project Manager",
            code="PROJECT_MANAGER",
            permission_codes=[
                "projects.read",
            ],
        )

        TenantRoleService.update_role(
            tenant_id=self.tenant.id,
            role_id=role.id,
            permission_codes=[
                "projects.read",
                "projects.update",
            ],
        )

        permission_codes = set(
            role.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "projects.read",
            "projects.update",
        }

    def test_update_rejects_unknown_permission(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Project Manager",
            code="PROJECT_MANAGER",
        )

        with pytest.raises(ValidationError):
            TenantRoleService.update_role(
                tenant_id=self.tenant.id,
                role_id=role.id,
                permission_codes=[
                    "invalid.permission",
                ],
            )

    def test_update_other_tenant_role_is_denied(self):
        role = TenantRoleService.create_role(
            tenant_id=self.other_tenant.id,
            name="Support",
            code="SUPPORT",
        )

        with pytest.raises(ResourceNotFoundError):
            TenantRoleService.update_role(
                tenant_id=self.tenant.id,
                role_id=role.id,
                name="Hijacked Role",
            )

    def test_delete_custom_role(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Temporary Role",
            code="TEMPORARY_ROLE",
        )

        role_id = role.id

        TenantRoleService.delete_role(
            tenant_id=self.tenant.id,
            role_id=role_id,
        )

        assert not Role.objects.filter(
            id=role_id
        ).exists()

    def test_delete_other_tenant_role_is_denied(self):
        role = TenantRoleService.create_role(
            tenant_id=self.other_tenant.id,
            name="Support",
            code="SUPPORT",
        )

        with pytest.raises(ResourceNotFoundError):
            TenantRoleService.delete_role(
                tenant_id=self.tenant.id,
                role_id=role.id,
            )

        assert Role.objects.filter(
            id=role.id
        ).exists()

    def test_system_role_cannot_be_updated(self):
        system_role = Role.objects.get(
            code="ADMIN",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        with pytest.raises(ResourceNotFoundError):
            TenantRoleService.update_role(
                tenant_id=self.tenant.id,
                role_id=system_role.id,
                name="Modified Admin",
            )

    def test_system_role_cannot_be_deleted(self):
        system_role = Role.objects.get(
            code="ADMIN",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        with pytest.raises(ResourceNotFoundError):
            TenantRoleService.delete_role(
                tenant_id=self.tenant.id,
                role_id=system_role.id,
            )

        assert Role.objects.filter(
            id=system_role.id
        ).exists()

    def test_get_custom_role(self):
        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Accountant",
            code="ACCOUNTANT",
        )

        fetched = TenantRoleService.get_role(
            tenant_id=self.tenant.id,
            role_id=role.id,
        )

        assert fetched.id == role.id

    def test_get_system_role(self):
        system_role = Role.objects.get(
            code="OWNER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        fetched = TenantRoleService.get_role(
            tenant_id=self.tenant.id,
            role_id=system_role.id,
        )

        assert fetched.id == system_role.id

    def test_get_other_tenant_role_is_not_visible(self):
        role = TenantRoleService.create_role(
            tenant_id=self.other_tenant.id,
            name="Support",
            code="SUPPORT",
        )

        # get_role must not expose another tenant's custom role.
        with pytest.raises(ResourceNotFoundError):
            TenantRoleService.get_role(
                tenant_id=self.tenant.id,
                role_id=role.id,
            )