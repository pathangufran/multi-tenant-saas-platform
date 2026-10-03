from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    TaskCreateSerializer,
    TaskUpdateSerializer,
    TaskResponseSerializer,
)
from .services import TaskService
from apps.common.rbac import TenantServiceRBACPermission

class ProjectTaskCreateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tasks.create"
    
    def post(self,request,project_id):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id
        
        serializer = TaskCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        task = TaskService.create_task(
            tenant_id=tenant_id,
            project_id=project_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        response = TaskResponseSerializer(task)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class ProjectTaskListView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tasks.read"
    
    def get(self,request,project_id):
        tenant_id = request.tenant_context.tenant_id
        
        tasks = TaskService.list_project_tasks(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        response = TaskResponseSerializer(
            tasks,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ProjectTaskDetailsView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,
    ]
    required_permission = "tasks.read"
    
    def get(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id
        
        task = TaskService.get_task(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        response = TaskResponseSerializer(task)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ProjectTaskUpdateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tasks.update"
    
    def patch(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id
        
        serializer = TaskUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        task = TaskService.update_task(
            tenant_id=tenant_id,
            task_id=task_id,
            data=serializer.validated_data,
        )
        response = TaskResponseSerializer(task)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class ProjectTaskDeleteView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tasks.delete"
    
    def delete(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id
        
        task = TaskService.delete_task(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        
        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )