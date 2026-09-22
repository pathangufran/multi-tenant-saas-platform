import pytest
from apps.tenants.models import Permission, Role
from apps.tenants.rbac_service import (
    RBACService,
)

@pytest.mark.django_db
class TestPermissionAssignment:

    def setup_method(self):
        RBACService.initialize_permissions()

        from apps.tenants.models import Tenant

        self.tenant = Tenant.objects.create(
            name="Test Corporation",
            slug="test-corporation",
            status=Tenant.Status.ACTIVE,
        )

        self.role = Role.objects.create(
            name="Custom Manager",
            code="CUSTOM_MANAGER",
            scope=Role.Scope.TENANT,
            tenant=self.tenant,
            is_system_role=False,
        )

        self.permission = Permission.objects.get(
            code="projects.read"
        )

    def test_assign_permission_to_role(self):
        assigned = RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert assigned.id == self.permission.id

        assert self.role.permissions.filter(
            code="projects.read"
        ).exists()

    def test_assign_permission_is_idempotent(self):
        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert self.role.permissions.filter(
            code="projects.read"
        ).count() == 1

    def test_assign_unknown_permission_fails(self):
        with pytest.raises(Exception) as exc_info:
            RBACService.assign_permission(
                role_id=self.role.id,
                permission_code="projects.unknown",
            )

        assert "Permission not found" in str(
            exc_info.value
        )

    def test_assign_permission_to_unknown_role_fails(self):
        import uuid

        with pytest.raises(Exception) as exc_info:
            RBACService.assign_permission(
                role_id=uuid.uuid4(),
                permission_code="projects.read",
            )

        assert "Role not found" in str(
            exc_info.value
        )

    def test_remove_permission(self):
        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert self.role.permissions.filter(
            code="projects.read"
        ).exists()

        RBACService.remove_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert not self.role.permissions.filter(
            code="projects.read"
        ).exists()

    def test_remove_absent_permission_is_idempotent(self):
        RBACService.remove_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert not self.role.permissions.filter(
            code="projects.read"
        ).exists()

    def test_replace_permissions(self):
        RBACService.replace_permissions(
            role_id=self.role.id,
            permission_codes=[
                "projects.read",
                "projects.create",
                "tasks.read",
            ],
        )

        permission_codes = set(
            self.role.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "projects.read",
            "projects.create",
            "tasks.read",
        }

    def test_replace_permissions_removes_old_permissions(self):
        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.create",
        )

        RBACService.replace_permissions(
            role_id=self.role.id,
            permission_codes=[
                "tasks.read",
            ],
        )

        permission_codes = set(
            self.role.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "tasks.read",
        }

    def test_replace_permissions_rejects_unknown_permission(self):
        with pytest.raises(Exception) as exc_info:
            RBACService.replace_permissions(
                role_id=self.role.id,
                permission_codes=[
                    "projects.read",
                    "invalid.permission",
                ],
            )

        assert "Unknown permissions" in str(
            exc_info.value
        )

        assert not self.role.permissions.exists()

    def test_replace_permissions_removes_duplicate_codes(self):
        RBACService.replace_permissions(
            role_id=self.role.id,
            permission_codes=[
                "projects.read",
                "projects.read",
                "tasks.read",
            ],
        )

        permission_codes = set(
            self.role.permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == {
            "projects.read",
            "tasks.read",
        }

    def test_get_role_permissions(self):
        RBACService.replace_permissions(
            role_id=self.role.id,
            permission_codes=[
                "projects.read",
                "projects.create",
                "tasks.read",
            ],
        )

        permissions = RBACService.get_role_permissions(
            role_id=self.role.id
        )

        permission_codes = list(
            permissions.values_list(
                "code",
                flat=True,
            )
        )

        assert permission_codes == sorted(
            [
                "projects.read",
                "projects.create",
                "tasks.read",
            ]
        )

    def test_has_permission_returns_true(self):
        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert RBACService.has_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        ) is True

    def test_has_permission_returns_false(self):
        assert RBACService.has_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        ) is False

    def test_role_permissions_are_independent(self):
        another_role = Role.objects.create(
            name="Another Role",
            code="ANOTHER_ROLE",
            scope=Role.Scope.TENANT,
            tenant=self.tenant,
            is_system_role=False,
        )

        RBACService.assign_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        )

        assert RBACService.has_permission(
            role_id=self.role.id,
            permission_code="projects.read",
        ) is True

        assert RBACService.has_permission(
            role_id=another_role.id,
            permission_code="projects.read",
        ) is False