from uuid import UUID
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    ProjectCreateSerializer,
    ProjectUpdateSerializer,
    ProjectResponseSerializer,
)
from .services import ProjectService

class ProjectCreateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id
        
        serializer = ProjectCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        project = ProjectService.create_project(
            tenant_id=tenant_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        response = ProjectResponseSerializer(project)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class ProjectListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        tenant_id = request.tenant_context.tenant_id
        
        projects = ProjectService.list_projects(
            tenant_id=tenant_id,
        )
        response = ProjectResponseSerializer(
            projects,
            many=True,    
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ProjectDetailView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request,project_id):
        tenant_id = request.tenant_context.tenant_id
        
        project = ProjectService.get_project(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        response = ProjectResponseSerializer(project)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ProjectUpdateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def patch(self,request,project_id):
        tenant_id = request.tenant_context.tenant_id
        
        serializer = ProjectUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        project = ProjectService.update_project(
            tenant_id=tenant_id,
            project_id=project_id,
            data=serializer.validated_data,
        )
        response = ProjectResponseSerializer(project)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ProjectDeleteView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def delete(self,request,project_id):
        tenant_id = request.tenant_context.tenant_id
        
        project = ProjectService.delete_project(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        
        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )