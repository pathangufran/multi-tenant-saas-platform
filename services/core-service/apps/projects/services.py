from uuid import UUID
from django.db import transaction
from .models import Project
from apps.common.exceptions import (
    ResourceNotFoundError,
)

class ProjectService:
    
    @staticmethod
    @transaction.atomic
    def create_project(
        *,
        tenant_id: UUID,
        user_id: UUID,
        name: str,
        description: str = "",
    ) -> Project:
        
        return Project.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            created_by=user_id,
            status=Project.Status.ACTIVE,
        )
        
    @staticmethod
    def list_projects(
        *,
        tenant_id: UUID,
    ):
        
        return Project.objects.filter(
            tenant_id=tenant_id,
        ).order_by("-created_at")
        
    @staticmethod
    def get_active_projects(
        *,
        tenant_id: UUID,
    ):
        
        return Project.objects.filter(
            tenant_id=tenant_id,
            status=Project.Status.ACTIVE,
        ).order_by("-created_at")
        
    @staticmethod
    @transaction.atomic
    def update_project(
        *,
        tenant_id: UUID,
        project_id: UUID,
        data: dict,
    ) -> Project:
        
        project = ProjectService.get_project(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        for field,value in data.items():
            setattr(project,field,value)
            
        project.save(
            update_fields=[
                *data.keys(),"updated_at",
            ]
        )
        
        return project
        
    @staticmethod
    @transaction.atomic
    def delete_project(
        *,
        tenant_id: UUID,
        project_id: UUID,
    ) -> None:
        
        project = ProjectService.get_project(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        
        project.delete()
        
    @staticmethod
    def get_project(
        *,
        tenant_id: UUID,
        project_id: UUID,
    ) -> Project:
        
        try:
            return Project.objects.get(
                tenant_id=tenant_id,
                id=project_id
            )
        except Project.DoesNotExist:
            raise ResourceNotFoundError(
                "Project not found."
            )