from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    TenantCreateSerializer,
    TenantResponseSerializer,
)
from .services import TenantService

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
        
        tenant = TenantService.get_user_tenant(
            user_id=request.user.id,
            tenant_id=tenant_id,
        )
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )