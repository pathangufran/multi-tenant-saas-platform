from django.db import transaction,IntegrityError
from .rbac_defaults import (
    DEFAULT_PERMISSIONS,
    DEFAULT_TENANT_ROLES,
)
from .models import (
    TenantMembership,Permission,Role,ObjectPermission
)
from apps.common.exceptions import (
    AuthorizationError,
    ConflictError,
    ValidationError,   
    ResourceNotFoundError,
)
from django.db.models import Q

class RBACService:
    
    @staticmethod
    @transaction.atomic
    def initialize_permissions():   
        permissions = dict()
        
        for permission_data in DEFAULT_PERMISSIONS:
            permission,_ = (
                Permission.objects.update_or_create(
                    code=permission_data["code"],
                        defaults={
                        "name": permission_data["name"],
                        "description": permission_data[
                            "description"
                        ],
                    },
                )
            )
            permissions[permission.code] = permission
            
        return permissions
    
    @staticmethod
    @transaction.atomic
    def initialize_tenant_roles(*,tenant):
        permissions = (
            RBACService.initialize_permissions()
        )
        
        roles = dict()
        
        for role_code,permission_codes in (
            DEFAULT_TENANT_ROLES.items()
        ):
            role,_ = Role.objects.update_or_create(
                tenant=tenant,
                code=role_code,
                defaults={
                    "name": role_code.title(),
                    "scope": Role.Scope.TENANT,
                    "is_system_role": True,
                },   
            )
            
            role.permissions.set(
                [
                    permissions[permission_code]
                    for permission_code in permission_codes
                ]
            )
            
            roles[role.code] = role
            
        return roles
        
    @staticmethod
    def get_system_tenant_role(
        *,
        tenant,
        role_code: str,
    ) -> Role:
        return Role.objects.get(
            tenant=tenant,
            code=role_code,
            scope=Role.Scope.TENANT,
            is_system_role=True,
        )
        
    @staticmethod
    @transaction.atomic
    def assign_role_to_membership(
        *,
        membership,
        role: Role,
    ):
        if role.scope != Role.Scope.TENANT:
            raise ValueError(
                "Only tenant roles can be assigned "
                "to tenant memberships."
            )

        if role.tenant_id != membership.tenant_id:
            raise ValueError(
                "Role does not belong to the "
                "membership tenant."
            )

        membership.role = role
        membership.save(
            update_fields=[
                "role",
                "updated_at",
            ]
        )

        return membership
    
    @staticmethod
    @transaction.atomic
    def assign_permission(
        *,
        role_id,
        permission_code: str,
    ) -> Permission:
        """
        Assign a permission to a role.

        The operation is idempotent:
        assigning an already assigned permission does not
        create a duplicate relationship.
        """
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Role not found."
            ) from exc
            
        try:
            permission = Permission.objects.get(
                code=permission_code
            )
        except Permission.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Permission not found."
            ) from exc
            
        role.permissions.add(permission)
        
        return permission
    
    @staticmethod
    @transaction.atomic
    def remove_permission(
        *,
        role_id,
        permission_code: str,
    ) -> None:
        """
        Remove a permission from a role.

        Removing an already absent permission is idempotent.
        """
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Role not found."
            ) from exc
            
        try:
            permission = Permission.objects.get(
                code=permission_code
            )
        except Permission.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Permission not found."
            ) from exc
            
        role.permissions.remove(permission)
        
    @staticmethod
    @transaction.atomic
    def replace_permissions(
        *,
        role_id,
        permission_codes: list[str],
    ) -> list[Permission]:
        """
        Replace all permissions assigned to a role.
        """
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Role not found."
            ) from exc
            
        normalized_codes = list(
            dict.fromkeys(
                code.strip()
                for code in permission_codes
                if code and code.strip()
            )
        )
        permissions = list(
            Permission.objects.filter(
                code__in=normalized_codes
            )
        )
        found_codes = {
            permission.code for permission in permissions
        }
        missing_codes = set(normalized_codes) - found_codes
        
        if missing_codes:
            raise ValidationError(
                f"Unknown permissions: {', '.join(sorted(missing_codes))}"
            )
            
        role.permissions.set(permissions)
        
        return permissions
    
    @staticmethod
    def get_role_permissions(
        *,
        role_id,
    ):
        """
        Return all permissions assigned to a role.
        """
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Role not found."
            ) from exc
            
        return role.permissions.all().order_by("code")
    
    @staticmethod
    def has_permission(
        *,
        role_id,
        permission_code: str,
    ) -> bool:
        """
        Check whether a user has a permission
        within a specific tenant.
        """
        
        return Permission.objects.filter(
            code=permission_code,
            roles__id=role_id,
        ).exists()
        
class PermissionCheckService:
    
    @staticmethod
    def has_permission(
        *,
        user_id,
        tenant_id,
        permission_code: str,
    ) -> bool:
        """
        Check whether a user has a permission
        within a specific tenant.
        """
        
        return TenantMembership.objects.filter(
            user_id=user_id,
            tenant_id=tenant_id,
            status=TenantMembership.Status.ACTIVE,
            role__permissions__code=permission_code,
        ).exists()
        
    @staticmethod
    def require_permission(
        *,
        user_id,
        tenant_id,
        permission_code: str,
    ) -> None:
        """
        Require a user to have a permission.

        Raises AuthorizationError when permission
        is not granted.
        """
        
        allowed = PermissionCheckService.has_permission(
            user_id=user_id,
            tenant_id=tenant_id,
            permission_code=permission_code,
        )
        
        if not allowed:
            raise AuthorizationError(
                f"Permission required: {permission_code}"
            )
            
    @staticmethod
    def get_user_permissions(
        *,
        user_id,
        tenant_id,
    ):
        """
        Return all permissions available to the user
        within the specified tenant.
        """
        
        membership = (
            TenantMembership.objects
            .filter(
                user_id=user_id,
                tenant_id=tenant_id,
                status=TenantMembership.Status.ACTIVE,
            )
            .select_related("role")
            .prefetch_related("role__permissions")
            .first()
        )
        
        if membership is None or membership.role is None:
            return []
        
        return (
            membership.role.permissions
            .all()
            .order_by("code")
        )
        
    @staticmethod
    def get_user_permission_codes(
        *,
        user_id,
        tenant_id,
    ) -> set[str]:
        """
        Return permission codes as a set for efficient
        repeated permission checks.
        """
        
        permissions = PermissionCheckService.get_user_permissions(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        
        return {
            permission.code
            for permission in permissions
        }
        
    @staticmethod
    def check_any_permission(
        *,
        user_id,
        tenant_id,
        permission_codes: list[str],
    ) -> bool:
        """
        Return True when the user has at least one
        of the requested permissions.
        """
        
        if not permission_codes:
            return False
        
        return (
            PermissionCheckService
            ._membership_queryset(
                user_id=user_id,
                tenant_id=tenant_id,
            )
            .filter(
                role__permissions__code__in=permission_codes,
            )
            .exists()
        )
        
    @staticmethod
    def check_all_permissions(
        *,
        user_id,
        tenant_id,
        permission_codes: list[str],
    ) -> bool:
        """
        Return True only when the user has every
        requested permission.
        """
        
        if not permission_codes:
            return True
        
        user_permissions = (
            PermissionCheckService
            .get_user_permission_codes(
                user_id=user_id,
                tenant_id=tenant_id,
            )
        )
        
        return set(permission_codes).issubset(
            user_permissions
        )
        
    @staticmethod
    def _membership_queryset(
        *,
        user_id,
        tenant_id,
    ):
        return TenantMembership.objects.filter(
            user_id=user_id,
            tenant_id=tenant_id,
            status=TenantMembership.Status.ACTIVE,
            role__isnull=False,
        )
        
class TenantRoleService:
    
    @staticmethod
    def list_roles(*,tenant_id,):
        """
        Return all tenant-scoped roles belonging to a tenant,
        plus predefined system tenant roles.
        """
        
        return (
            Role.objects
            .filter(
                scope=Role.Scope.TENANT,
            )
            .filter(
                Q(
                    tenant_id=tenant_id
                ) |
                Q(
                    tenant_id__isnull=True,
                    is_system_role=True,
                )
            )
            .prefetch_related("permissions")
            .order_by(
                "is_system_role",
                "code"
            ),
        )

    @staticmethod
    @transaction.atomic
    def create_role(
        *,
        tenant_id,
        name: str,
        code: str,
        description: str = "",
        permission_codes=None,
    ):
        """
        Create a custom tenant role.
        """
        
        normalized_code = code.strip().upper()
        
        if not normalized_code:
            raise ValidationError(
                "Role code cannot be empty."
            )
            
        if not name.strip():
            raise ValidationError(
                "Role name cannot be empty."
            )
            
        if Role.objects.filter(
            tenant_id=tenant_id,
            code=normalized_code,
            scope=Role.Scope.TENANT,
        ).exists():
            raise ConflictError(
                "A role with this code already exists."
            )
            
        permissions = []
        
        if permission_codes:
            permission_codes = list(
                dict.fromkeys(
                    code.strip()
                    for code in permission_codes
                    if code and code.strip()
                )
            )
            
            permissions = list(
                Permission.objects.filter(
                    code__in=permission_codes
                )
            )
            
            found_codes = (
                permission.code
                for permission in permissions
            )
            
            missing_codes = (
                set(permission_codes) - found_codes
            )
            
            if missing_codes:
                raise ValidationError(
                    "Unknown permissions: "
                    + ", ".join(
                        sorted(missing_codes)
                    )
                )
        
        try:
            role = Role.objects.create(
                tenant_id=tenant_id,
                name=name.strip(),
                code=normalized_code,
                scope=Role.Scope.TENANT,
                description=description.strip(),
                is_system_role=False,
            )
        except IntegrityError as exc:
            raise ConflictError(
                "A role with this code already exists."
            ) from exc
            
        if permissions:
            role.permissions.set(permissions)
            
        return 
    
    @staticmethod
    @transaction.atomic
    def update_role(
        *,
        tenant_id,
        role_id,
        name=None,
        description=None,
        permission_codes=None,
    ):
        """
        Update a custom tenant role.
        """
        
        role = TenantRoleService._get_custom_role(
            tenant_id=tenant_id,
            role_id=role_id,
        )
        
        if name is not None:
            normalized_name = name.strip()
            
            if not normalized_name:
                raise ValidationError(
                    
                )
                
            role.name = normalized_name
            
        if description is not None:
            role.description = description.strip()
            
        role.save()
        
        if permission_codes is not None:
            normalized_codes = list(
                dict.fromkeys(
                    code.strip()
                    for code in permission_codes
                    if code and code.strip()
                )
            )
            
            permissions = list(
                Permission.objects.filter(
                    code__in=normalized_codes
                )
            )
            
            found_codes = (
                permission.code
                for permission in permissions
            )
            
            missing_codes = (
                set(normalized_codes) - found_codes
            )

            if missing_codes:
                raise ValidationError(
                    "Unknown permissions: "
                    + ", ".join(
                        sorted(missing_codes)
                    )
                )

            role.permissions.set(permissions)
            
        return role
    
    @staticmethod
    @transaction.atomic
    def delete_role(
        *,
        tenant_id,
        role_id,
    ):
        """
        Delete a custom tenant role.

        System roles cannot be deleted.
        """
        
        role = TenantRoleService._get_custom_role(
            tenant_id=tenant_id,
            role_id=role_id,
        )
        
        role.delete()
        
    @staticmethod
    def get_role(
        *,
        tenant_id,
        role_id,
    ):
        """
        Return a role visible to the tenant.

        This includes:
        - custom tenant roles
        - system tenant roles
        """

        try:
            role = (
                Role.objects
                .prefetch_related("permissions")
                .get(
                    Q(
                        id=role_id,
                        scope=Role.Scope.TENANT,
                        tenant_id=tenant_id,
                    )
                    | 
                    Q(
                        id=role_id,
                        scope=Role.Scope.TENANT,
                        tenant_id__isnull=True,
                        is_system_role=True,
                    )
                )
            )
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Role not found."
            ) from exc   
            
    @staticmethod
    def _get_custom_role(
        *,
        tenant_id,
        role_id,
    ):
        """
        Return a tenant-owned custom role.

        System roles and roles belonging to another tenant
        cannot be modified through this service.
        """
        
        try:
            role = Role.objects.get(
                id=role_id,
                tenant_id=tenant_id,
                scope=Role.Scope.TENANT,
                is_system_role=False,
            )
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Custom tenant role not found."
            ) from exc
            
        return role
    
class ObjectPermissionService:
    
    @staticmethod
    @transaction.atomic
    def grant_user_permission(
        *,
        tenant_id,
        user_id,
        resource_type: str,
        resource_id,
        permission_code: str,
    ):
        """
        Grant a permission on a specific resource
        directly to a user.
        """
        
        ObjectPermissionService._validate_resource(
            resource_type=resource_type,
            resource_id=resource_id,
        )
        
        permission = (
            ObjectPermissionService
            ._get_permission(permission_code)
        )
        
        ObjectPermissionService._ensure_active_membership(
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        object_permission,_ = (
            ObjectPermission.objects.get_or_create(
                tenant_id=tenant_id,
                subject_type=(
                    ObjectPermission.SubjectType.USER
                ),
                subject_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
            )
        )
        
        return object_permission
    
    @staticmethod
    @transaction.atomic
    def grant_role_permission(
        *,
        tenant_id,
        role_id,
        resource_type: str,
        resource_id,
        permission_code: str,
    ):
        """
        Grant a permission on a specific resource
        to a tenant role.
        """
        
        ObjectPermissionService._validate_resource(
            resource_type=resource_type,
            resource_id=resource_id,
        )
        
        permission = (
            ObjectPermissionService
            ._get_permission(permission_code)
        )
        
        try:
            role = Role.objects.get(
                id=role_id,
                scope=Role.Scope.TENANT,
            )
        except Role.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Role not found"
            ) from exc
            
        if (
            not role.is_system_role
            and role.tenant_id != tenant_id
        ):
            raise ResourceNotFoundError(
                "Role not found."
            )
            
        object_permission,_ = (
            ObjectPermission.objects.get_or_create(
                tenant_id=tenant_id,
                subject_type=(
                    ObjectPermission.SubjectType.ROLE
                ),
                subject_id=role.id,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
            )
        )
        
        return object_permission
    
    @staticmethod
    @transaction.atomic
    def revoke_user_permission(
        *,
        tenant_id,
        user_id,
        resource_type: str,
        resource_id,
        permission_code: str,
    ):
        permission = (
            ObjectPermissionService
            ._get_permission(permission_code)
        )
        
        deleted,_ = (
            ObjectPermission.objects.filter(
                tenant_id=tenant_id,
                subject_type=(
                    ObjectPermission.SubjectType.USER
                ),
                subject_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
            ).delete()
        )
        
        return deleted > 0
    
    @staticmethod
    @transaction.atomic
    def revoke_role_permission(
        *,
        tenant_id,
        role_id,
        resource_type: str,
        resource_id,
        permission_code: str,
    ):
        permission = (
            ObjectPermissionService
            ._get_permission(permission_code)
        )
        
        deleted,_ = (
            ObjectPermission.objects.filter(
                tenant_id=tenant_id,
                subject_type=(
                    ObjectPermission.SubjectType.ROLE
                ),
                subject_id=role_id,
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
            ).delete()
        )
        
        return deleted > 0
    
    @staticmethod
    def has_object_permission(
        *,
        tenant_id,
        user_id,
        resource_type: str,
        resource_id,
        permission_code: str,
    ) -> bool:
        """
        Check object-level permission.

        Access is granted when either:
        1. The user has the permission directly, or
        2. One of the user's roles has the object permission.
        """
        
        permission = (
            ObjectPermissionService
            ._get_permission(permission_code)
        )
        
        if not ObjectPermissionService._has_active_membership(
            tenant_id=tenant_id,
            user_id=user_id,
        ):
            return False
        
        direct_access = ObjectPermission.objects.filter(
            tenant_id=tenant_id,
            subject_type=(
                ObjectPermission.SubjectType.USER
            ),
            subject_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
        ).exists()
        
        if direct_access:
            return True
        
        role_ids = TenantMembership.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            status=TenantMembership.Status.ACTIVE,
            role__isnull=False,
        ).values_list("role_id",flat=True,)
        
        return ObjectPermission.objects.filter(
            tenant_id=tenant_id,
            subject_type=(
                ObjectPermission.SubjectType.ROLE
            ),
            subject_id__in=role_ids,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
        ).exists()
        
    @staticmethod
    def _get_permission(permission_code):
        try:
            return Permission.objects.get(
                code=permission_code,
            )
        except Permission.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Permission not found."
            ) from exc
            
    @staticmethod
    def _has_active_membership(
        *,
        tenant_id,
        user_id,
    ):
        return TenantMembership.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            status=TenantMembership.Status.ACTIVE,
        ).exists()
        
    @staticmethod
    def _ensure_active_membership(
        *,
        tenant_id,
        user_id,
    ):
        if not ObjectPermissionService._has_active_membership(
            tenant_id=tenant_id,
            user_id=user_id,
        ):
            raise AuthorizationError(
                "User does not have an active tenant membership."
            )
            
    @staticmethod
    def _validate_resource(
        *,
        resource_type,
        resource_id,
    ):
        if not resource_type:
            raise ValidationError(
                "Resource type is required."
            )
            
        if not str(resource_type).strip():
            raise ValidationError(
                "Resource type cannot be empty."
            )
            
        if not resource_id:
            raise ValidationError(
                "Resource ID is required."
            )