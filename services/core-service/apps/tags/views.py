from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    TagCreateSerializer,
    TagResponseSerializer,
    TagUpdateSerializer,
    TaskTagCreateSerializer,
)
from .services import TagService
from apps.common.rbac import TenantServiceRBACPermission

class TagCreateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.create"

    def post(self,request):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id

        serializer = TagCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        response = TagResponseSerializer(tag)

        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class TagListView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,
    ]
    required_permission = "tags.read"

    def get(self,request):
        tenant_id = request.tenant_context.tenant_id

        tags = TagService.list_tags(
            tenant_id=tenant_id,
        )
        response = TagResponseSerializer(
            tags,
            many=True,
        )

        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )

class TagDetailView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.read"

    def get(self,request,tag_id):
        tenant_id = request.tenant_context.tenant_id

        tag = TagService.get_tag(
            tenant_id=tenant_id,
            tag_id=tag_id,
        )
        response = TagResponseSerializer(tag)

        return Response(
            response.data,
            status=status.HTTP_200_OK,    
        )

class TagUpdateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.update"

    def patch(self,request,tag_id):
        tenant_id = request.tenant_context.tenant_id

        serializer = TagUpdateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        tag = TagService.update_tag(
            tenant_id=tenant_id,
            tag_id=tag_id,
            name=serializer.validated_data["name"],
        )

        response = TagResponseSerializer(tag)

        return Response(
            response.data,
            status=status.HTTP_200_OK,    
        )

class TagDeleteView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.delete"

    def delete(self,request,tag_id):
        tenant_id = request.tenant_context.tenant_id

        TagService.delete_tag(
            tenant_id=tenant_id,
            tag_id=tag_id,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

class TaskTagCreateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.assign"

    def post(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id

        serializer = TaskTagCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        task_tag = TagService.attach_tag_to_task(
            tenant_id=tenant_id,
            task_id=task_id,
            **serializer.validated_data,
        )
        response = TagResponseSerializer(
            task_tag.tag,
        )

        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )

class TaskTagListView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.read"

    def get(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id

        tags = TagService.list_task_tags(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        response = TagResponseSerializer(
            tags,
            many=True,
        )

        return Response(
            response.data,
            status=status.HTTP_200_OK,    
        )

class TaskTagDeleteView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "tags.assign"

    def delete(self,request,task_id,tag_id):
        tenant_id = request.tenant_context.tenant_id

        TagService.remove_tag_from_task(
            tenant_id=tenant_id,
            task_id=task_id,
            tag_id=tag_id,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )