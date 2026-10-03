import os
import requests
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
)

class TenantServiceRBACPermission(BasePermission):
    """
    Permission class that delegates RBAC checks to tenant-service.

    Core-service does not own RBAC data. It asks tenant-service whether
    the authenticated user has the required permission inside the
    current tenant.
    """
    
    message = "You do not have permission to perform this action."
    
    def has_permission(self,request,view):
        
        if not IsAuthenticated().has_permission(request,view):
            return False
        
        tenant_context = getattr(
            request,"tenant_context",None,
        )
        user_id = getattr(
            request,"authenticated_user_id",None,
        )
        required_permission = getattr(
            view,"required_permission",None,
        )
        
        if tenant_context is None:
            return False
        
        if not user_id:
            return False
        
        if not required_permission:
            return False
        
        tenant_id = getattr(
            tenant_context,"tenant_id",None
        )
        
        if not tenant_id:
            return False
        
        rbac_check_url = os.getenv("TENANT_SERVICE_RBAC_CHECK_URL")
        service_key = os.getenv("TENANT_SERVICE_INTERNAL_SERVICE_KEY")
        
        if not rbac_check_url or not service_key:
            return False
        
        payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "permission_code": required_permission,
        }

        headers = {
            "X-Internal-Service-Key": service_key,
        }
        
        try:
            response = requests.post(
                rbac_check_url,
                json=payload,
                headers=headers,
                timeout=2.5,
            )
        except requests.RequestException:
            return False
        
        if response.status_code != 200:
            return False
        
        try:
            response_data = response.json()
        except (TypeError,ValueError):
            return False
        
        return bool(response_data.get("allowed",False))