from uuid import UUID
from django.http import JsonResponse
from .context import (
    clear_tenant_context,set_tenant_context
)
from .context_service import TenantContextService
from apps.common.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
)

class TenantContextMiddleware:
    
    def __init__(self,get_response):
        self.get_response = get_response
        
    def __call__(self,request):
        tenant_id = request.headers.get(
            "X-Tenant-ID",
        )
        
        if not tenant_id:
            return self.get_response(request)
        
        user_id = getattr(
            request,
            "authenticated_user_id",
            None,
        )
        if not user_id:
            return JsonResponse(
                {
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": (
                            "Authenticated user is required "
                            "for tenant context."
                        ),
                    }
                },
                status=401,
            )
        
        try:
            user_id = UUID(str(user_id))
            tenant_id = UUID(tenant_id)
        except ValueError:
            return JsonResponse(
                {
                    "error": {
                        "code": "INVALID_TENANT_CONTEXT",
                        "message": (
                            "Invalid tenant context."
                        ),
                    }
                },
                status=400,
            )
            
        try:
            context = TenantContextService.resolve(
                user_id=user_id,
                tenant_id=tenant_id,
            )
        except ResourceNotFoundError:
            return JsonResponse(
                {
                    "error": {
                        "code": "TENANT_ACCESS_DENIED",
                        "message": (
                            "User does not have access "
                            "to this tenant."
                        ),
                    }
                },
                status=403,
            )
        except AuthorizationError as exc:
            return JsonResponse(
                {
                    "error": {
                        "code": "AUTHORIZATION_ERROR",
                        "message": str(exc),
                    }
                },
                status=403,
            )
            
        token = set_tenant_context(context)
        
        try:
            request.tenant_context = context
            return self.get_response(request)
        finally:
            clear_tenant_context(token)
        