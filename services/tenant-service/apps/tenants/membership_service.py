from uuid import UUID
from django.db import IntegrityError,transaction
from django.utils import timezone
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from .models import Tenant,TenantMembership
from .isolation import TenantIsolationService

class TenantMembershipService:
    
    @staticmethod
    @transaction.atomic
    def create_membership(
        *,
        tenant_id,
        user_id,
        status=TenantMembership.Status.ACTIVE,
    ) -> TenantMembership:
        try:
            tenant = Tenant.objects.get(
                id=tenant_id,
            )
            
        except Tenant.DoesNotExist:
            raise ResourceNotFoundError(
                message="Tenant not found."
            )
            
        if TenantMembership.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
        ).exists():
            raise ConflictError(
                message=(
                    "User is already a member of this tenant."
                )
            )
            
        joined_at = (
            timezone.now()
            if status == TenantMembership.Status.ACTIVE
            else None
        )
        
        try:
            return TenantMembership.objects.create(
                tenant=tenant,
                user_id=user_id,
                status=status,
                joined_at=joined_at,
            )
            
        except IntegrityError:
            raise ConflictError(
                message=(
                    "User is already a member of this tenant."
                )
            )
            
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