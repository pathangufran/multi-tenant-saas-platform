from uuid import UUID
from django.db import transaction
from apps.tasks.models import Task
from .models import Comment
from apps.common.exceptions import (
    ResourceNotFoundError,
)

class CommentService:
    
    @staticmethod
    def _get_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
    ) -> Task:
        
        try:
            return Task.objects.get(
                tenant_id=tenant_id,
                id=task_id,
            )
        except Task.DoesNotExist:
            raise ResourceNotFoundError(
                "Task not found."
            )
            
    @staticmethod
    @transaction.atomic
    def create_comment(
        *,
        tenant_id: UUID,
        task_id: UUID,
        user_id: UUID,
        content: dict,
    ) -> Comment:
        
        CommentService._get_task(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        
        return Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task_id,
            content=content,
            created_by=user_id,
        )
        
    @staticmethod
    def list_task_comments(
        *,
        tenant_id: UUID,
        task_id: UUID,
    ) -> Comment:
        
        return Comment.objects.filter(
            tenant_id=tenant_id,
            task_id=task_id,
        ).order_by("-created_at")
        
    @staticmethod
    def list_user_comments(
        *,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Comment:
        
        return Comment.objects.filter(
            tenant_id=tenant_id,
            created_by=user_id,
        ).order_by("-created_at")
        
    @staticmethod
    @transaction.atomic
    def update_comment(
        *,
        tenant_id: UUID,
        comment_id: UUID,
        content: dict,
    ) -> Comment:
        
        comment = CommentService.get_comment(
            tenant_id=tenant_id,
            comment_id=comment_id,
        )
        comment.content = content
        comment.save(
            update_fields=[
                "content","updated_at",
            ]
        )

        return comment
    
    @staticmethod
    @transaction.atomic
    def delete_comment(
        *,
        tenant_id: UUID,
        comment_id: UUID,
    ) -> None:
        
        comment = CommentService.get_comment(
            tenant_id=tenant_id,
            comment_id=comment_id,
        )
        
        comment.delete()
        
    @staticmethod
    def get_comment(
        *,
        tenant_id: UUID,
        comment_id: UUID,
    ) -> Comment:
        
        try:
            return Comment.objects.get(
                tenant_id=tenant_id,
                id=comment_id,
            )
        except Comment.DoesNotExist:
            raise ResourceNotFoundError(
                "Comment not found."
            )
            
        