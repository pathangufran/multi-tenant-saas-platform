from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    AttachmentCreateSerializer,
    AttachmentResponseSerializer,
)
from .services import AttachmentService

class TaskAttachmentCreateView(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id

        serializer = AttachmentCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        attachment = AttachmentService.create_attachment(
            tenant_id=tenant_id,
            task_id=task_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        response = AttachmentResponseSerializer(
            attachment,
        )

        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class TaskAttachmentListView(APIView):
    
    permission_classes = [IsAuthenticated]
        
    def get(self,request,task_id):
        tenant_id = request.tenant_context.tenant_id

        attachments = AttachmentService.list_task_attachments(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        response = AttachmentResponseSerializer(
            attachments,
            many=True,
        )

        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )

class TaskAttachmentDetailView(APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self,request,attachment_id):
        tenant_id = request.tenant_context.tenant_id

        attachment = AttachmentService.get_attachment(
            tenant_id=tenant_id,
            attachment_id=attachment_id,
        )
        response = AttachmentResponseSerializer(
            attachment,
        )

        return Response(
            response.data,
            status=status.HTTP_200_OK,
        
        )

class TaskAttachmentDeleteView(APIView):
    
    permission_classes = [IsAuthenticated]

    def delete(self,request,attachment_id):
        tenant_id = request.tenant_context.tenant_id

        AttachmentService.delete_attachment(
            tenant_id=tenant_id,
            attachment_id=attachment_id,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )