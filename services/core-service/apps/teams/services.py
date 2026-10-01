from uuid import UUID
from django.db import IntegrityError,transaction
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from .models import Team

class TeamService:
    
    @staticmethod
    @transaction.atomic
    def create_team(
        *,
        tenant_id: UUID,
        user_id: UUID,
        name: str,
        description: str = ""
    ) -> Team:
        
        try:
            with transaction.atomic():
                return Team.objects.create(
                    tenant_id=tenant_id,
                    name=name,
                    description=description,
                    created_by=user_id,
                )
        except IntegrityError:
            raise ConflictError(
                "A team with this name already exists."
            )
        
    @staticmethod
    def list_teams(
        *,
        tenant_id: UUID,
    ):
        
        return Team.objects.filter(
            tenant_id=tenant_id
        ).order_by("-created_at")
        
    @staticmethod
    @transaction.atomic
    def update_team(
        *,
        tenant_id: UUID,
        team_id: UUID,
        data: dict,
    ) -> Team:
        
        team = TeamService.get_team(
            tenant_id=tenant_id,
            team_id=team_id,
        )
        for field,value in data.items():
            setattr(team,field,value)
        
        try:    
            team.save(
                update_fields=[
                    *data.keys(),"updated_at",
                ]
            )
        except IntegrityError:
            raise ConflictError(
                "A team with this name already exists."
            )
            
        return team
    
    @staticmethod
    @transaction.atomic
    def delete_team(
        *,
        tenant_id: UUID,
        team_id: UUID,
    ) -> None:
        
        team = TeamService.get_team(
            tenant_id=tenant_id,
            team_id=team_id,
        )
        
        team.delete()
        
    @staticmethod
    def get_team(
        *,
        tenant_id: UUID,
        team_id: UUID,
    ) -> Team:
        
        try:
            return Team.objects.get(
                tenant_id=tenant_id,
                id=team_id,
            )
        except Team.DoesNotExist:
            raise ResourceNotFoundError(
                "Team not found."
            )
    
    