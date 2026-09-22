from django.db import transaction
from .rbac_defaults import (
    DEFAULT_PERMISSIONS,
    DEFAULT_TENANT_ROLES,
)
from .models import (
    TenantMembership,Permission,Role
)
from apps.common.exceptions import (
    AuthorizationError,
    ConflictError,
    ValidationError,   
    ResourceNotFoundError,
)

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