from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    CommentCreateSerializer,
    CommentResponseSerializer,
    CommentUpdateSerializer,
)
from .services import CommentService
from apps.common.rbac import TenantServiceRBACPermission

class TaskCommentCreateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "comments.create"

    def post(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id

        serializer = CommentCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        comment = CommentService.create_comment(
            tenant_id=tenant_id,
            task_id=task_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        response = CommentResponseSerializer(comment)

        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class TaskCommentListView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "comments.read"
    
    def get(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id

        comments = CommentService.list_task_comments(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        response = CommentResponseSerializer(
            comments,
            many=True,
        )

        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )

class TaskCommentDetailView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "comments.read"

    def get(self,request,comment_id):
        tenant_id = request.tenant_context.tenant_id

        comment = CommentService.get_comment(
            tenant_id=tenant_id,
            comment_id=comment_id,
        )
        response = CommentResponseSerializer(comment)

        return Response(
            response.data,
            status=status.HTTP_200_OK,    
        )

class TaskCommentUpdateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "comments.update"

    def patch(self,request,comment_id):
        tenant_id = request.tenant_context.tenant_id

        serializer = CommentUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        comment = CommentService.update_comment(
            tenant_id=tenant_id,
            comment_id=comment_id,
            content=serializer.validated_data,
        )
        response = CommentResponseSerializer(comment)

        return Response(
            response.data,
            status=status.HTTP_200_OK,    
        )

class TaskCommentDeleteView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,
    ]
    required_permission = "comments.delete"

    def delete(self,request,comment_id):
        tenant_id = request.tenant_context.tenant_id

        comment = CommentService.delete_comment(
            tenant_id=tenant_id,
            comment_id=comment_id,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )