import uuid
import pytest
from apps.common.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from apps.tenants.models import (
    Tenant, TenantMembership, ObjectPermission, Role
)
from apps.tenants.rbac_service import (
    ObjectPermissionService,
    RBACService,
    TenantRoleService,
)

@pytest.mark.django_db
class TestObjectPermissions:

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

        self.custom_role = (
            TenantRoleService.create_role(
                tenant_id=self.tenant.id,
                name="Project Manager",
                code="PROJECT_MANAGER",
            )
        )

        self.project_id = uuid.uuid4()

    def test_grant_user_object_permission(self):
        object_permission = (
            ObjectPermissionService
            .grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
        )

        assert (
            object_permission.tenant_id
            == self.tenant.id
        )

        assert (
            object_permission.subject_type
            == ObjectPermission.SubjectType.USER
        )

        assert (
            object_permission.subject_id
            == self.user_id
        )

        assert (
            object_permission.resource_type
            == "project"
        )

        assert (
            object_permission.resource_id
            == self.project_id
        )

    def test_direct_user_permission_allows_access(self):
        ObjectPermissionService.grant_user_permission(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is True
        )

    def test_missing_object_permission_denies_access(self):
        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_revoke_user_permission(self):
        ObjectPermissionService.grant_user_permission(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        removed = (
            ObjectPermissionService
            .revoke_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
        )

        assert removed is True

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_revoke_missing_user_permission_is_idempotent(self):
        removed = (
            ObjectPermissionService
            .revoke_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
        )

        assert removed is False

    def test_grant_role_object_permission(self):
        object_permission = (
            ObjectPermissionService
            .grant_role_permission(
                tenant_id=self.tenant.id,
                role_id=self.custom_role.id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
        )

        assert (
            object_permission.subject_type
            == ObjectPermission.SubjectType.ROLE
        )

        assert (
            object_permission.subject_id
            == self.custom_role.id
        )

    def test_role_object_permission_allows_member(self):
        self.membership.role = self.custom_role
        self.membership.save(
            update_fields=[
                "role",
                "updated_at",
            ]
        )

        ObjectPermissionService.grant_role_permission(
            tenant_id=self.tenant.id,
            role_id=self.custom_role.id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is True
        )

    def test_role_object_permission_does_not_cross_tenant(self):
        self.membership.role = self.custom_role
        self.membership.save(
            update_fields=[
                "role",
                "updated_at",
            ]
        )

        ObjectPermissionService.grant_role_permission(
            tenant_id=self.tenant.id,
            role_id=self.custom_role.id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.other_tenant.id,
                user_id=self.other_user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_other_tenant_role_cannot_receive_object_permission(self):
        other_role = TenantRoleService.create_role(
            tenant_id=self.other_tenant.id,
            name="Other Role",
            code="OTHER_ROLE",
        )

        with pytest.raises(ResourceNotFoundError):
            ObjectPermissionService.grant_role_permission(
                tenant_id=self.tenant.id,
                role_id=other_role.id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )

    def test_unknown_permission_is_rejected(self):
        with pytest.raises(ResourceNotFoundError):
            ObjectPermissionService.grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="invalid.permission",
            )

    def test_unknown_user_cannot_receive_direct_permission(self):
        with pytest.raises(AuthorizationError):
            ObjectPermissionService.grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=uuid.uuid4(),
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )

    def test_inactive_membership_cannot_receive_permission(self):
        self.membership.status = (
            TenantMembership.Status.SUSPENDED
        )

        self.membership.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        with pytest.raises(AuthorizationError):
            ObjectPermissionService.grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )

    def test_removed_membership_has_no_object_access(self):
        ObjectPermissionService.grant_user_permission(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        self.membership.status = (
            TenantMembership.Status.REMOVED
        )

        self.membership.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_same_user_different_tenant_isolated(self):
        ObjectPermissionService.grant_user_permission(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.other_tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_different_resource_is_denied(self):
        ObjectPermissionService.grant_user_permission(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.update",
        )

        another_project_id = uuid.uuid4()

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=another_project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_different_permission_is_denied(self):
        ObjectPermissionService.grant_user_permission(
            tenant_id=self.tenant.id,
            user_id=self.user_id,
            resource_type="project",
            resource_id=self.project_id,
            permission_code="projects.read",
        )

        assert (
            ObjectPermissionService.has_object_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
            is False
        )

    def test_same_resource_type_and_id_are_unique(self):
        first = (
            ObjectPermissionService
            .grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
        )

        second = (
            ObjectPermissionService
            .grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
                permission_code="projects.update",
            )
        )

        assert first.id == second.id

        assert (
            ObjectPermission.objects.filter(
                tenant=self.tenant,
                subject_type=(
                    ObjectPermission.SubjectType.USER
                ),
                subject_id=self.user_id,
                resource_type="project",
                resource_id=self.project_id,
            ).count()
            == 1
        )

    def test_invalid_resource_type_is_rejected(self):
        with pytest.raises(ValidationError):
            ObjectPermissionService.grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="",
                resource_id=self.project_id,
                permission_code="projects.update",
            )

    def test_invalid_resource_id_is_rejected(self):
        with pytest.raises(ValidationError):
            ObjectPermissionService.grant_user_permission(
                tenant_id=self.tenant.id,
                user_id=self.user_id,
                resource_type="project",
                resource_id=None,
                permission_code="projects.update",
            )