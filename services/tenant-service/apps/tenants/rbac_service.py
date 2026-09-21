from django.db import transaction
from .rbac_defaults import (
    DEFAULT_PERMISSIONS,
    DEFAULT_TENANT_ROLES,
)
from .models import Permission,Role

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