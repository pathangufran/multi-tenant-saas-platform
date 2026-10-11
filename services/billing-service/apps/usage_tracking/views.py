from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .serializers import (
    UsageSetSerializer,
    UsageAdjustmentSerializer,
    UsageRecordSerializer,
)
from .services import UsageService

class AdminUsageCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        tenant_id = request.tenant_context.tenant_id
        serializer = UsageSetSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        record = UsageService.set_usage(
            tenant_id,
            **serializer.validated_data,
        )
        response = UsageRecordSerializer(record)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminUsageListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        tenant_id = request.tenant_context.tenant_id
        
        records = UsageService.list_usage(
            tenant_id,
        )
        response = UsageRecordSerializer(
            records,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminUsageDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,metric):
        tenant_id = request.tenant_context.tenant_id
        
        record = UsageService.get_usage(
            tenant_id,
            metric,
        )
        response = UsageRecordSerializer(record)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminUsageAdjustmentView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        tenant_id = request.tenant_context.tenant_id
        serializer = UsageAdjustmentSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        record = UsageService.adjust_usage(
            tenant_id,
            **serializer.validated_data,
        )
        response = UsageRecordSerializer(record)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )