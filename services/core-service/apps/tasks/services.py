from uuid import UUID
from django.db import transaction
from apps.common.exceptions import ResourceNotFoundError
from apps.projects.models import Project
from .models import Task
from apps.common.domain_rules import CoreDomainRules

class TaskService:
    
    @staticmethod
    def _get_project(
        *,
        tenant_id: UUID,
        project_id: UUID,
    ) -> Project:
        
        return CoreDomainRules.ensure_project_belongs_to_tenant(
            tenant_id=tenant_id,
            project_id=project_id,
        )
            
    @staticmethod
    @transaction.atomic
    def create_task(
        *,
        tenant_id: UUID,
        project_id: UUID,
        user_id: UUID,
        title: str,
        description: str = "",
        priority: str = Task.Priority.MEDIUM,
        assignee_id: UUID | None = None,
        due_date=None,
    ) -> Task:
        
        TaskService._get_project(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        
        return Task.objects.create(
            tenant_id=tenant_id,
            project_id=project_id,
            title=title,
            description=description,
            priority=priority,
            status=Task.Status.TODO,
            assignee_id=assignee_id,
            due_date=due_date,
            created_by=user_id,
        )
        
    @staticmethod
    def list_project_tasks(
        *,
        tenant_id: UUID,
        project_id: UUID,
    ):
        
        CoreDomainRules.ensure_project_belongs_to_tenant(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        
        return Task.objects.filter(
            tenant_id=tenant_id,
            project_id=project_id,
        ).order_by("-created_at")
        
    @staticmethod
    def list_assigned_tasks(
        *,
        tenant_id: UUID,
        assignee_id: UUID,
    ):
        return Task.objects.filter(
            tenant_id=tenant_id,
            assignee_id=assignee_id,
        ).order_by("-created_at")
        
    @staticmethod
    @transaction.atomic
    def update_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
        data: dict,
    ) -> Task:
        
        task = TaskService.get_task(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        for field,value in data.items():
            setattr(task,field,value)
            
        task.save(
            update_fields=[
                *data.keys(),"updated_at",
            ]
        )
        
        return task
    
    @staticmethod
    @transaction.atomic
    def delete_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
    ) -> None:
        
        task = TaskService.get_task(
            tenant_id=tenant_id,
            task_id=task_id,
        )
        
        task.delete()
        
    @staticmethod
    def get_task(
        *,
        tenant_id: UUID,
        task_id: UUID,
    ) -> Task:
        
        return CoreDomainRules.ensure_task_belongs_to_tenant(
            tenant_id=tenant_id,
            task_id=task_id,
        )