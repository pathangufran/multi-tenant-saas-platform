from rest_framework.permissions import BasePermission
from .rbac_service import PermissionCheckService

class RBACPermission(BasePermission):
    """
    Generic DRF permission class backed by the RBAC engine.

    Views declare the required permission(s):

        required_permission = "projects.read"

    or:

        required_permissions = [
            "projects.read",
            "projects.update",
        ]

    Permission mode:

        permission_mode = "all"

    or:

        permission_mode = "any"
    """
    
    message = "You do not have permission to perform this action."
    
    def has_permission(self,request,view):
        user_id = self._get_user_id(request)
        
        if user_id is None:
            return False
        
        tenant_id = self._get_tenant_id(request)
        
        if tenant_id is None:
            return False
        
        permissions = self._get_required_permissions(view)
        
        if not permissions:
            return False
        
        mode = getattr(
            view,
            "permission_mode",
            "all",
        )
        
        if mode == "any":
            return PermissionCheckService.check_any_permission(
                user_id=user_id,
                tenant_id=tenant_id,
                permission_codes=permissions,
            )
            
        return PermissionCheckService.check_all_permissions(
            user_id=user_id,
            tenant_id=tenant_id,
            permission_codes=permissions,
        )
        
    @staticmethod
    def _get_user_id(request):
        """
        Get the authenticated user identity.

        Tenant service does not own the Auth Service User model,
        therefore we use the authenticated user ID supplied by
        the authentication layer.
        """
        
        authenticated_user_id = getattr(
            request,
            "authenticated_user_id",
            None,
        )
        
        if authenticated_user_id is not None:
            return authenticated_user_id
        
        user = getattr(request, "user", None)
        
        if user is not None:
            user_id = getattr(user, "id", None)
            
            if user_id is not None:
                return user_id
            
        return None
    
    @staticmethod
    def _get_tenant_id(request):
        """
        Get the tenant ID from the trusted tenant context.

        The permission class does not resolve X-Tenant-ID itself.
        Tenant resolution belongs to the tenant-context middleware.
        """
        
        tenant_context = getattr(
            request,
            "tenant_context",
            None,
        )
        
        if tenant_context is None:
            return None
        
        return getattr(
            tenant_context,
            "tenant_id",
            None,
        )
        
    @staticmethod
    def _get_required_permissions(view):
        single_permission = getattr(
            view,
            "required_permission",
            None,
        )
        
        if single_permission:
            return [single_permission]
        
        permissions = getattr(
            view,
            "required_permissions",
            None,
        )
        
        if not permissions:
            return []
        
        return list(
            dict.fromkeys(
                permission
                for permission in permissions
                if permission
            )
        )