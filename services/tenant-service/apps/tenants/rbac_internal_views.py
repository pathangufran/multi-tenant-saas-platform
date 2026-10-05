import os
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .rbac_service import PermissionCheckService

class InternalRBACPermissionCheckView(APIView):
    """
    Internal endpoint used by other services to verify tenant RBAC
    permissions.

    This endpoint is not intended for public/client access.
    Authentication is performed using an internal service key.
    """
    
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self,request):
        expected_service_key = os.getenv("INTERNAL_SERVICE_KEY")
        provided_service_key = request.headers.get("X-Internal-Service-Key")
        
        if (
            not expected_service_key
            or not provided_service_key
            or provided_service_key != expected_service_key
        ):
            return Response(
                {"detail": "Invalid internal service credentials."},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        user_id = request.data.get("user_id")
        tenant_id = request.data.get("tenant_id")
        permission_code = request.data.get("permission_codes")
        
        if not user_id:
            return Response(
                {"detail": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if not tenant_id:
            return Response(
                {"detail": "tenant_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if not permission_code:
            return Response(
                {"detail": "permission_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        allowed = PermissionCheckService.has_permission(
            user_id=user_id,
            tenant_id=tenant_id,
            permission_code=permission_code,
        )
        
        return Response(
            {"allowed": bool(allowed)},
            status=status.HTTP_200_OK,
        )