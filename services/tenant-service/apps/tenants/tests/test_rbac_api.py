import uuid
import pytest
from rest_framework.test import APIRequestFactory
from apps.tenants.models import Tenant, TenantMembership,Role
from apps.tenants.rbac_service import RBACService

@pytest.mark.django_db
class TestRBACAPI:

    def setup_method(self):
        RBACService.initialize_permissions()
        RBACService.initialize_tenant_roles()

        self.factory = APIRequestFactory()

        self.tenant = Tenant.objects.create(
            name="API Tenant",
            slug=f"api-tenant-{uuid.uuid4().hex[:8]}",
            status=Tenant.Status.ACTIVE,
        )

        self.user_id = uuid.uuid4()

        self.membership = TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
            role=Role.objects.get(
                code="OWNER",
                scope=Role.Scope.TENANT,
                is_system_role=True,
            ),
        )

    def _request(self, method, path, data=None):
        request = getattr(
            self.factory,
            method.lower(),
        )(
            path,
            data=data,
            format="json",
        )

        request.authenticated_user_id = (
            self.user_id
        )

        from apps.tenants.context import TenantContext

        request.tenant_context = TenantContext(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
        )

        return request

    def test_role_list_endpoint(self):
        from apps.tenants.views import (
            TenantRoleListCreateView,
        )

        request = self._request(
            "GET",
            "/api/v1/tenants/roles/",
        )

        response = (
            TenantRoleListCreateView.as_view()(
                request
            )
        )

        assert response.status_code == 200

        codes = {
            role["code"]
            for role in response.data
        }

        assert "OWNER" in codes
        assert "ADMIN" in codes
        assert "VIEWER" in codes

    def test_create_role_endpoint(self):
        from apps.tenants.views import (
            TenantRoleListCreateView,
        )

        request = self._request(
            "POST",
            "/api/v1/tenants/roles/",
            data={
                "name": "Project Manager",
                "code": "PROJECT_MANAGER",
                "description": (
                    "Project management role."
                ),
                "permission_codes": [
                    "projects.read",
                    "projects.update",
                ],
            },
        )

        response = (
            TenantRoleListCreateView.as_view()(
                request
            )
        )

        assert response.status_code == 201

        assert response.data["code"] == (
            "PROJECT_MANAGER"
        )

    def test_role_detail_endpoint(self):
        from apps.tenants.views import (
            TenantRoleDetailView,
        )

        role = Role.objects.get(
            code="OWNER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        request = self._request(
            "GET",
            f"/api/v1/tenants/roles/{role.id}/",
        )

        response = (
            TenantRoleDetailView.as_view()(
                request,
                role_id=role.id,
            )
        )

        assert response.status_code == 200
        assert response.data["code"] == "OWNER"

    def test_update_custom_role_endpoint(self):
        from apps.tenants.rbac_service import (
            TenantRoleService,
        )
        from apps.tenants.views import (
            TenantRoleDetailView,
        )

        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Old Name",
            code="CUSTOM_ROLE",
        )

        request = self._request(
            "PATCH",
            f"/api/v1/tenants/roles/{role.id}/",
            data={
                "name": "Updated Name",
            },
        )

        response = (
            TenantRoleDetailView.as_view()(
                request,
                role_id=role.id,
            )
        )

        assert response.status_code == 200
        assert response.data["name"] == (
            "Updated Name"
        )

    def test_delete_custom_role_endpoint(self):
        from apps.tenants.rbac_service import (
            TenantRoleService,
        )
        from apps.tenants.views import (
            TenantRoleDetailView,
        )

        role = TenantRoleService.create_role(
            tenant_id=self.tenant.id,
            name="Temporary",
            code="TEMPORARY",
        )

        request = self._request(
            "DELETE",
            f"/api/v1/tenants/roles/{role.id}/",
        )

        response = (
            TenantRoleDetailView.as_view()(
                request,
                role_id=role.id,
            )
        )

        assert response.status_code == 204

    def test_assign_membership_role_endpoint(self):
        from apps.tenants.views import (
            MembershipRoleView,
        )

        role = Role.objects.get(
            code="MANAGER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        request = self._request(
            "POST",
            (
                "/api/v1/tenants/memberships/"
                f"{self.membership.id}/role/"
            ),
            data={
                "role_id": str(role.id),
            },
        )

        response = (
            MembershipRoleView.as_view()(
                request,
                membership_id=self.membership.id,
            )
        )

        assert response.status_code == 200
        assert response.data["code"] == "MANAGER"

    def test_remove_membership_role_endpoint(self):
        from apps.tenants.views import (
            MembershipRoleView,
        )

        request = self._request(
            "DELETE",
            (
                "/api/v1/tenants/memberships/"
                f"{self.membership.id}/role/"
            ),
        )

        response = (
            MembershipRoleView.as_view()(
                request,
                membership_id=self.membership.id,
            )
        )

        assert response.status_code == 204

    def test_user_object_permission_endpoint(self):
        from apps.tenants.views import (
            UserObjectPermissionView,
        )

        resource_id = uuid.uuid4()

        request = self._request(
            "POST",
            "/api/v1/tenants/object-permissions/users/",
            data={
                "user_id": str(self.user_id),
                "resource_type": "project",
                "resource_id": str(resource_id),
                "permission_code": "projects.update",
            },
        )

        response = (
            UserObjectPermissionView.as_view()(
                request
            )
        )

        assert response.status_code == 201
        assert "id" in response.data

    def test_role_object_permission_endpoint(self):
        from apps.tenants.views import (
            RoleObjectPermissionView,
        )

        role = Role.objects.get(
            code="MANAGER",
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )

        resource_id = uuid.uuid4()

        request = self._request(
            "POST",
            "/api/v1/tenants/object-permissions/roles/",
            data={
                "role_id": str(role.id),
                "resource_type": "project",
                "resource_id": str(resource_id),
                "permission_code": "projects.update",
            },
        )

        response = (
            RoleObjectPermissionView.as_view()(
                request
            )
        )

        assert response.status_code == 201
        assert "id" in response.data