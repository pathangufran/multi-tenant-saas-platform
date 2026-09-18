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
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        response = TenantResponseSerializer(tenant)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        

