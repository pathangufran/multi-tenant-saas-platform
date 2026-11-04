import uuid
import pytest
from types import SimpleNamespace
from apps.tenants.models import (
    Tenant, TenantMembership, Role
)
from apps.tenants.permissions import RBACPermission
from apps.tenants.rbac_service import RBACService

@pytest.mark.django_db
class TestRBACPermission:

    def setup_method(self):
        RBACService.initialize_permissions()

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

        TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.owner_user_id,
            status=TenantMembership.Status.ACTIVE,
            role=self.owner_role,
        )

        TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.viewer_user_id,
            status=TenantMembership.Status.ACTIVE,
            role=self.viewer_role,
        )

        self.permission = RBACPermission()

    def _request(self, user_id, tenant_id=None):
        tenant_context = None

        if tenant_id is not None:
            tenant_context = SimpleNamespace(
                tenant_id=tenant_id,
                user_id=user_id,
            )

        return SimpleNamespace(
            authenticated_user_id=user_id,
            tenant_context=tenant_context,
        )

    def _view(
        self,
        required_permission=None,
        required_permissions=None,
        permission_mode="all",
    ):
        attributes = {
            "permission_mode": permission_mode,
        }

        if required_permission is not None:
            attributes["required_permission"] = (
                required_permission
            )

        if required_permissions is not None:
            attributes["required_permissions"] = (
                required_permissions
            )

        return SimpleNamespace(**attributes)

    def test_owner_can_access_project_create(self):
        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permission="projects.create",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is True

    def test_viewer_cannot_access_project_create(self):
        request = self._request(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permission="projects.create",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_viewer_can_access_project_read(self):
        request = self._request(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permission="projects.read",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is True

    def test_missing_user_is_denied(self):
        request = self._request(
            user_id=None,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permission="projects.read",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_missing_tenant_context_is_denied(self):
        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=None,
        )

        view = self._view(
            required_permission="projects.read",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_missing_required_permission_is_denied(self):
        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view()

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_unknown_permission_is_denied(self):
        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permission="does.not.exist",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_cross_tenant_access_is_denied(self):
        other_tenant = Tenant.objects.create(
            name="Other Tenant",
            slug=f"other-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=other_tenant.id,
        )

        view = self._view(
            required_permission="projects.create",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_all_permissions_requires_every_permission(self):
        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permissions=[
                "projects.read",
                "projects.create",
            ],
            permission_mode="all",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is True

    def test_all_permissions_denies_when_one_is_missing(self):
        request = self._request(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permissions=[
                "projects.read",
                "projects.create",
            ],
            permission_mode="all",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_any_permissions_allows_when_one_matches(self):
        request = self._request(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permissions=[
                "projects.create",
                "projects.read",
            ],
            permission_mode="any",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is True

    def test_any_permissions_denies_when_none_match(self):
        request = self._request(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permissions=[
                "projects.create",
                "projects.delete",
            ],
            permission_mode="any",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_empty_permission_list_is_denied(self):
        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permissions=[],
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_duplicate_permissions_are_normalized(self):
        request = self._request(
            user_id=self.viewer_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permissions=[
                "projects.read",
                "projects.read",
            ],
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is True

    def test_fallback_to_request_user_id(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                id=self.owner_user_id,
            ),
            tenant_context=SimpleNamespace(
                tenant_id=self.tenant.id,
            ),
        )

        view = self._view(
            required_permission="projects.create",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is True

    def test_authenticated_user_id_takes_precedence(self):
        request = SimpleNamespace(
            authenticated_user_id=self.viewer_user_id,
            user=SimpleNamespace(
                id=self.owner_user_id,
            ),
            tenant_context=SimpleNamespace(
                tenant_id=self.tenant.id,
            ),
        )

        view = self._view(
            required_permission="projects.create",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False

    def test_inactive_membership_is_denied(self):
        membership = TenantMembership.objects.get(
            tenant=self.tenant,
            user_id=self.owner_user_id,
        )

        membership.status = (
            TenantMembership.Status.SUSPENDED
        )

        membership.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        request = self._request(
            user_id=self.owner_user_id,
            tenant_id=self.tenant.id,
        )

        view = self._view(
            required_permission="projects.create",
        )

        assert self.permission.has_permission(
            request,
            view,
        ) is False