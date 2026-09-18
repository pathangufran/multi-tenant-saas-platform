from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    TenantCreateSerializer,
    TenantUpdateSerializer,
    TenantResponseSerializer,
)
from .services import TenantService
from apps.common.exceptions import (
    ResourceNotFoundError,
)

class TenantCreateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        
        serializer = TenantCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            tenant = TenantService.create_tenant(
                name=serializer.validated_data["name"],
                slug=serializer.validated_data["slug"],
                owner_user_id=request.user.id,
            )
        except ValueError as exc:
            return Response(
                data={"details":str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        response = TenantResponseSerializer(tenant)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class TenantListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        
        tenants = TenantService.get_user_tenants(
            user_id=request.user.id,
        )
        serializer = TenantResponseSerializer(
            tenants,
            many=True,
        )
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,    
        )
        
class CurrentTenantView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request,tenant_id):
        
        try:
            tenant = TenantService.get_user_tenant(
                user_id=request.user.id,
                tenant_id=tenant_id,
            )
        except ResourceNotFoundError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
            
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
    def patch(self,request,tenant_id):
        
        serializer = TenantUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            tenant = TenantService.update_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
                name = serializer.validated_data.get("name"),
                slug = serializer.validated_data.get("slug")
            )
        except ResourceNotFoundError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        response = TenantResponseSerializer(tenant)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class TenantSuspendView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request,tenant_id):
        
        try:
            tenant = TenantService.suspend_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
            )
        except ResourceNotFoundError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
class TenantActivateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request,tenant_id):
        
        try:
            tenant = TenantService.activate_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
            )
        except ValueError as exc:
            return Response(
                data={"details":str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
class TenantDeactivateView(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self,request,tenant_id):
        
        try:
            tenant = TenantService.deactivate_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
            )
        except ValueError as exc:
            return Response(
                data={"details":str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TenantResponseSerializer(tenant)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,    
        )
        
        
        