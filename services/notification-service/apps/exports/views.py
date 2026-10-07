from uuid import UUID
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Export
from .serializers import (
    ExportCreateSerializer,
    ExportResponseSerializer,
)
from .services import ExportService
from .tasks import generate_export

class ExportCreateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id
        
        serializer = ExportCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        export = ExportService.create_export(
            tenant_id=tenant_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        generate_export.delay(
            str(export.id),
            []
        )
        response = ExportResponseSerializer(export)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class ExportListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id
        
        exports = ExportService.list_exports(
            tenant_id=tenant_id,
            user_id=user_id,
        )
        response = ExportResponseSerializer(
            exports,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ExportDetailView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request,export_id):
        tenant_id = request.tenant_context.tenant_id
        
        export = ExportService.get_export(
            tenant_id=tenant_id,
            export_id=export_id,
        )
        response = ExportResponseSerializer(export)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ExportDownloadView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request,export_id):
        tenant_id = request.tenant_context.tenant_id
        
        export = ExportService.get_export(
            tenant_id=tenant_id,
            export_id=export_id,
        )
        download_url = ExportService.get_download_url(
            export=export
        )
        
        return Response(
            {
                "id": str(export.id),
                "file_name": export.file_name,
                "download_url": download_url,
            },
            status=status.HTTP_200_OK,
        )