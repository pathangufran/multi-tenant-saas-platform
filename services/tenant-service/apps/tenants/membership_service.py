from uuid import UUID
from django.db import IntegrityError,transaction
from django.utils import timezone
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from .models import Tenant,TenantMembership,Role
from .isolation import TenantIsolationService

class TenantMembershipService:
    
    @staticmethod
    @transaction.atomic
    def create_membership(
        *,
        tenant_id,
        user_id,
        role: Role,
        status=TenantMembership.Status.ACTIVE,
    ) -> TenantMembership:
        
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Tenant not found."
            ) from exc
        
        if role.scope != Role.Scope.TENANT:
            raise ValueError(
                "Membership requires a tenant role."
            )
        
        if (
            role.tenant_id is not None
            and role.tenant_id != tenant_id
        ):
            raise ValueError(
                "Role does not belong to this tenant."
            )
            
        try:
            membership = TenantMembership.objects.create(
                tenant_id=tenant_id,
                user_id=user_id,
                role=role,
                status=status,
                joined_at=(
                    timezone.now()
                    if status
                    == TenantMembership.Status.ACTIVE
                    else None
                ),
            )
        except IntegrityError as exc:
            raise ConflictError(
                "User is already a member of this tenant."
            ) from exc
        
        return membership
        
            
    @staticmethod
    @transaction.atomic
    def activate_membership(
        *,
        membership_id,
        tenant_id: UUID,
    ) -> TenantMembership:
        try:
            membership = (
                TenantMembership.objects
                .select_for_update()
                .get(
                    id=membership_id,
                    tenant_id=tenant_id,    
                )
            )
        except TenantMembership.DoesNotExist:
            raise ResourceNotFoundError(
                message="Membership not found."
            )
        
        TenantIsolationService.ensure_tenant_access(
            tenant_id=membership.tenant_id,
        )
            
        if membership.status == TenantMembership.Status.REMOVED:
            raise ConflictError(
                message="Removed membership cannot be activated."
            )
            
        membership.status == TenantMembership.Status.ACTIVE
        
        if membership.joined_at is None:
            membership.joined_at = timezone.now()

        membership.save(
            update_fields=["status","joined_at","updated_at",],
        )
        
        return membership
    
    @staticmethod
    @transaction.atomic
    def suspend_membership(
        *,
        membership_id,
        tenant_id: UUID,
    ) -> TenantMembership:
        try:
            membership = (
                TenantMembership.objects
                .select_for_update()
                .get(
                    id=membership_id,
                    tenant_id=tenant_id,    
                )
            )  
        except TenantMembership.DoesNotExist:
            raise ResourceNotFoundError(
                message="Membership not found."
            )
            
        TenantIsolationService.ensure_tenant_access(
            tenant_id=membership.tenant_id,
        )
        
        if membership.status == TenantMembership.Status.REMOVED:
            raise ConflictError(
                message="Removed membership cannot be suspended."
            )

        membership.status = TenantMembership.Status.SUSPENDED

        membership.save(
            update_fields=["status","updated_at",],
        )
        
        return membership
    
    @staticmethod
    @transaction.atomic
    def remove_membership(
        *,
        membership_id,
        tenant_id: UUID,
    ) -> TenantMembership:
        try:
            membership = (
                TenantMembership.objects
                .select_for_update()
                .get(
                    id=membership_id,
                    tenant_id=tenant_id,
                )
            )
        except TenantMembership.DoesNotExist:
            raise ResourceNotFoundError(
                message="Membership not found."
            )
            
        TenantIsolationService.ensure_tenant_access(
            tenant_id=membership.tenant_id,
        )
            
        if membership.status == TenantMembership.Status.REMOVED:
            raise ConflictError(
                message="Membership is already removed."
            )

        membership.status = TenantMembership.Status.REMOVED

        membership.save(
            update_fields=["status","updated_at",],
        )
        
        return membership
    
    @staticmethod
    @transaction.atomic
    def assign_role(
        *,
        tenant_id: UUID,
        role: Role,
        membership_id,
    ):
        if role.scope != Role.Scope.TENANT:
            raise ValueError(
                "Only tenant roles can be assigned."
            )
        
        if (
            role.tenant_id is not None
            and role.tenant_id != tenant_id
        ):
            raise ValueError(
                "Role does not belong to this tenant."
            )
            
        try:
            membership = (
                TenantMembership.objects
                .select_for_update()
                .get(
                    id=membership_id,
                    tenant_id=tenant_id,
                )
            )
        except TenantMembership.DoesNotExist:
            raise ResourceNotFoundError(
                
            )
            
        membership.role = role
        membership.save(
            update_fields=[
                "role","updated_at",
            ]
        )
        
        return membership