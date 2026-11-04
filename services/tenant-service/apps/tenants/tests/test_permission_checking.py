import uuid
import pytest
from apps.tenants.models import (
    Tenant, TenantMembership,Permission,Role
)
from apps.tenants.rbac_service import (
    RBACService,
    PermissionCheckService,
)

@pytest.mark.django_db
class TestPermissionChecking:

    def setup_method(self):
        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug=f"acme-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        roles = RBACService.initialize_tenant_roles(
            tenant=self.tenant
        )

        self.owner_role = roles["OWNER"]
        self.viewer_role = roles["VIEWER"]

        self.owner_user_id = uuid.uuid4()
        self.viewer_user_id = uuid.uuid4()
        self.no_role_user_id = uuid.uuid4()

        self.owner_membership = (
            TenantMembership.objects.create(
                tenant=self.tenant,
                user_id=self.owner_user_id,
                status=TenantMembership.Status.ACTIVE,
                role=self.owner_role,
            )
        )

        self.viewer_membership = (
            TenantMembership.objects.create(
                tenant=self.tenant,
                user_id=self.viewer_user_id,
                status=TenantMembership.Status.ACTIVE,
                role=self.viewer_role,
            )
        )

    def test_owner_has_project_create_permission(self):
        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.create",
        ) is True

    def test_viewer_does_not_have_project_create_permission(self):
        assert PermissionCheckService.has_permission(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.create",
        ) is False

    def test_viewer_has_project_read_permission(self):
        assert PermissionCheckService.has_permission(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.read",
        ) is True

    def test_unknown_user_has_no_permission(self):
        assert PermissionCheckService.has_permission(
            user_id=self.no_role_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.read",
        ) is False

    def test_unknown_permission_returns_false(self):
        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
            permission_code="permission.does.not.exist",
        ) is False

    def test_inactive_membership_has_no_permission(self):
        self.owner_membership.status = (
            TenantMembership.Status.SUSPENDED
        )
        self.owner_membership.save(
            update_fields=["status", "updated_at"]
        )

        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.create",
        ) is False

    def test_removed_membership_has_no_permission(self):
        self.owner_membership.status = (
            TenantMembership.Status.REMOVED
        )
        self.owner_membership.save(
            update_fields=["status", "updated_at"]
        )

        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.create",
        ) is False

    def test_cross_tenant_permission_is_denied(self):
        other_tenant = Tenant.objects.create(
            name="Other Corporation",
            slug=f"other-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=other_tenant.id,
            permission_code="projects.create",
        ) is False

    def test_same_user_in_different_tenants_is_isolated(self):
        other_tenant = Tenant.objects.create(
            name="Other Corporation",
            slug=f"other-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        TenantMembership.objects.create(
            tenant=other_tenant,
            user_id=self.owner_user_id,
            status=TenantMembership.Status.ACTIVE,
            role=self.viewer_role,
        )

        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.create",
        ) is True

        assert PermissionCheckService.has_permission(
            user_id=self.owner_user_id,
            tenant_id=other_tenant.id,
            permission_code="projects.create",
        ) is False

    def test_get_user_permissions(self):
        permissions = (
            PermissionCheckService.get_user_permissions(
                user_id=self.owner_user_id,
                tenant_id=self.tenant.id,
            )
        )

        permission_codes = {
            permission.code
            for permission in permissions
        }

        assert permission_codes == set(
            Permission.objects.values_list(
                "code",
                flat=True,
            )
        )

    def test_get_viewer_permissions(self):
        permissions = (
            PermissionCheckService.get_user_permissions(
                user_id=self.viewer_user_id,
                tenant_id=self.tenant.id,
            )
        )

        permission_codes = {
            permission.code
            for permission in permissions
        }

        assert permission_codes == {
            "tenant.read",
            "projects.read",
            "tasks.read",
        }

    def test_user_without_membership_has_no_permissions(self):
        permissions = (
            PermissionCheckService.get_user_permissions(
                user_id=self.no_role_user_id,
                tenant_id=self.tenant.id,
            )
        )

        assert list(permissions) == []

    def test_get_user_permission_codes(self):
        permission_codes = (
            PermissionCheckService
            .get_user_permission_codes(
                user_id=self.viewer_user_id,
                tenant_id=self.tenant.id,
            )
        )

        assert permission_codes == {
            "tenant.read",
            "projects.read",
            "tasks.read",
        }

    def test_require_permission_allows_authorized_user(self):
        PermissionCheckService.require_permission(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
            permission_code="projects.create",
        )

    def test_require_permission_rejects_unauthorized_user(self):
        from apps.common.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            PermissionCheckService.require_permission(
                user_id=self.viewer_user_id,
                tenant_id=self.tenant.id,
                permission_code="projects.create",
            )

    def test_check_any_permission_returns_true(self):
        assert PermissionCheckService.check_any_permission(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_codes=[
                "projects.create",
                "projects.read",
            ],
        ) is True

    def test_check_any_permission_returns_false(self):
        assert PermissionCheckService.check_any_permission(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_codes=[
                "projects.create",
                "projects.delete",
            ],
        ) is False

    def test_check_any_permission_empty_list(self):
        assert PermissionCheckService.check_any_permission(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_codes=[],
        ) is False

    def test_check_all_permissions_returns_true(self):
        assert PermissionCheckService.check_all_permissions(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_codes=[
                "tenant.read",
                "projects.read",
                "tasks.read",
            ],
        ) is True

    def test_check_all_permissions_returns_false(self):
        assert PermissionCheckService.check_all_permissions(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_codes=[
                "projects.read",
                "projects.create",
            ],
        ) is False

    def test_check_all_permissions_empty_list(self):
        assert PermissionCheckService.check_all_permissions(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
            permission_codes=[],
        ) is True