from uuid import UUID
from apps.common.exceptions import ResourceNotFoundError
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.tags.models import Tag,TaskTag

class CoreDomainRules:
    """Cross-domain integrity and tenant-isolation rules for Core Service."""
    
    @staticmethod
    def ensure_same_tenant(
        *,
        tenant_id: UUID,
        resource_tenant_id: UUID,
    ) -> None:
        
        if tenant_id != resource_tenant_id:
            raise ResourceNotFoundError(
                "Resource not found."
            )
            
    @staticmethod
    def ensure_project_belongs_to_tenant(
        *,
        tenant_id: UUID,
        project_id: UUID,
    ) -> Project:
        
        try:
            return Project.objects.get(
                id=project_id,
                tenant_id=tenant_id,
            )
        except Project.DoesNotExist:
            raise ResourceNotFoundError(
                "Project not found."
            )
            
    @staticmethod
    def ensure_task_belongs_to_tenant(
        *, 
        tenant_id: UUID, 
        task_id: UUID
    ) -> Task:
        
        try:
            return Task.objects.get(
                id=task_id, 
                tenant_id=tenant_id
            )
        except Task.DoesNotExist:
            raise ResourceNotFoundError(
                "Task not found."
            )
            
    @staticmethod
    def ensure_task_belongs_to_project(
        *,
        tenant_id: UUID,
        task_id: UUID,
        project_id: UUID,
    ) -> Task:
        
        try:
            return Task.objects.get(
                id=task_id,
                tenant_id=tenant_id,
                project_id=project_id,
            )
        except Task.DoesNotExist:
            raise ResourceNotFoundError(
                "Task does not belong to the \
                specified project."
            )
            
    @staticmethod
    def ensure_tag_belongs_to_tenant(
        *,
        tenant_id: UUID,
        tag_id: UUID,
    ) -> Tag:
        
        try:
            return Tag.objects.get(
                id=tag_id,
                tenant_id=tenant_id,
            )
        except Tag.DoesNotExist:
            raise ResourceNotFoundError(
                "Tag not found."
            )
            
    @staticmethod
    def ensure_task_tag_belongs_to_tenant(
        *,
        tenant_id: UUID,
        task_tag_id: UUID,   
    ) -> TaskTag:
        
        try:
            return (
                TaskTag.objects.select_related("tag").get(
                    id=task_tag_id,
                    tenant_id=tenant_id,
                    tag__tenant_id=tenant_id,
                )
            )
        except TaskTag.DoesNotExist:
            raise ResourceNotFoundError(
                "Task tag not found."
            )
            
    @staticmethod
    def ensure_task_and_tag_same_tenant(
        *, 
        tenant_id: UUID, 
        task_id: UUID, 
        tag_id: UUID
    ) -> tuple[Task, Tag]:
        
        task = CoreDomainRules.ensure_task_belongs_to_tenant(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        tag = CoreDomainRules.ensure_tag_belongs_to_tenant(
            tenant_id=tenant_id,
            tag_id=tag_id,
        )
        
        return task, tag