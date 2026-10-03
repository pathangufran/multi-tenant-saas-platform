from uuid import UUID
from django.db import transaction
from apps.common.exceptions import ResourceNotFoundError
from apps.tasks.models import Task
from .models import Attachment
from apps.common.domain_rules import CoreDomainRules

class AttachmentService:

    @staticmethod
    def _get_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
    ) -> Task:
        
        return CoreDomainRules.ensure_task_belongs_to_tenant(
            tenant_id=tenant_id,
            task_id=task_id,
        )

    @staticmethod
    @transaction.atomic
    def create_attachment(
        *,
        tenant_id: UUID,
        task_id: UUID,
        user_id: UUID,
        s3_key: str,
        filename: str,
        content_type: str,
        size: int,
    ) -> Attachment:
        
        AttachmentService._get_task(
            tenant_id=tenant_id,
            task_id=task_id,
        )

        return Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task_id,
            s3_key=s3_key,
            filename=filename,
            content_type=content_type,
            size=size,
            created_by=user_id,
        )
        
    @staticmethod
    def list_task_attachments(
        *,
        tenant_id: UUID,
        task_id: UUID,
    ) -> Attachment:
        
        return Attachment.objects.filter(
            tenant_id=tenant_id,
            task_id=task_id,
        ).order_by("-created_at")
        
    @staticmethod
    def list_user_attachments(
        *,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Attachment:
        
        return Attachment.objects.filter(
            tenant_id=tenant_id,
            created_by=user_id,
        ).order_by("-created_at")

    @staticmethod
    @transaction.atomic
    def delete_attachment(
        *,
        tenant_id: UUID,
        attachment_id: UUID,
    ) -> None:
        
        attachment = AttachmentService.get_attachment(
            tenant_id=tenant_id,
            attachment_id=attachment_id,
        )

        attachment.delete()
        
    @staticmethod
    def get_attachment(
        *,
        tenant_id: UUID,
        attachment_id: UUID,
    ) -> Attachment:
        
        try:
            return Attachment.objects.get(
                tenant_id=tenant_id,
                id=attachment_id,
            )
        except Attachment.DoesNotExist:
            raise ResourceNotFoundError(
                "Attachment not found."
            )