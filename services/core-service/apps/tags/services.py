from uuid import UUID
from django.db import IntegrityError, transaction
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from apps.tasks.models import Task
from .models import Tag, TaskTag
from apps.common.domain_rules import CoreDomainRules

class TagService:

    @staticmethod
    @transaction.atomic
    def create_tag(
        *,
        tenant_id: UUID,
        user_id: UUID,
        name: str,
    ) -> Tag:
        
        try:
            return Tag.objects.create(
                tenant_id=tenant_id,
                name=name,
                created_by=user_id,
            )
        except IntegrityError:
            raise ConflictError(
                "A tag with this name already exists."
            )
            
    @staticmethod
    def list_tags(
        *,
        tenant_id,
    ):
        
        return Tag.objects.filter(
            tenant_id=tenant_id,
        ).order_by("name")

    @staticmethod
    def list_task_tags(
        *,
        tenant_id,
        task_id,
    ):
        
        CoreDomainRules.ensure_task_belongs_to_tenant(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        
        return Tag.objects.filter(
            tenant_id=tenant_id,
            task_tags__tenant_id=tenant_id,
            task_tags__task_id=task_id,
        ).distinct().order_by("name")

    @staticmethod
    @transaction.atomic
    def update_tag(
        *,
        tenant_id: UUID,
        tag_id: UUID,
        name: str,
    ) -> Tag:
        
        tag = TagService.get_tag(
            tenant_id=tenant_id,
            tag_id=tag_id,
        )

        tag.name = name

        try:
            tag.save(
                update_fields=[
                    "name","updated_at",
                ]
            )
        except IntegrityError:
            raise ConflictError(
                "A tag with this name already exists."
            )

        return tag

    @staticmethod
    @transaction.atomic
    def delete_tag(
        *,
        tenant_id: UUID,
        tag_id: UUID,
    ) -> None:
        
        tag = TagService.get_tag(
            tenant_id=tenant_id,
            tag_id=tag_id,
        )

        tag.delete()

    @staticmethod
    @transaction.atomic
    def attach_tag_to_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
        tag_id: UUID,
    ) -> Tag:
        
        _, tag = CoreDomainRules.ensure_task_and_tag_same_tenant(
            tenant_id=tenant_id,
            task_id=task_id,
            tag_id=tag_id,
        )

        try:
            TaskTag.objects.create(
                tenant_id=tenant_id,
                task_id=task_id,
                tag=tag,
            )
        except IntegrityError:
            raise ConflictError(
                "Tag is already attached to this task."
            )
            
        return tag

    @staticmethod
    @transaction.atomic
    def remove_tag_from_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
        tag_id: UUID,
    ) -> None:
        
        task_tag = TagService.get_task_tag(
            tenant_id=tenant_id,
            task_id=task_id,
            tag_id=tag_id,
        )

        task_tag.delete()
        
    @staticmethod
    def get_tag(
        *,
        tenant_id: UUID,
        tag_id: UUID,   
    ) -> Tag:
        
        return CoreDomainRules.ensure_tag_belongs_to_tenant(
            tenant_id=tenant_id,
            tag_id=tag_id,
        )
            
    @staticmethod
    def get_task_tag(
        *,
        tenant_id: UUID,
        task_id: UUID,
        tag_id: UUID,
    ) -> Tag:
        
        try:
            return TaskTag.objects.get(
                tenant_id=tenant_id,
                task_id=task_id,
                tag_id=tag_id,
                tag__tenant_id=tenant_id,
            )
        except TaskTag.DoesNotExist:
            raise ResourceNotFoundError(
                "TaskTag not found."
            )