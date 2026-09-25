from uuid import UUID
from django.db import IntegrityError,transaction
from django.utils import timezone
from apps.common.exceptions import (
    AuthorizationError,
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
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
    
class TenantMembershipRoleService:
    
    @staticmethod
    def assign_role(
        *,
        tenant_id,
        membership_id,
        role_id,
    ):
        """
        Assign a tenant role to an existing membership.

        Only tenant-scoped roles can be assigned.
        Platform roles are never valid here.
        """

        with transaction.atomic():
            try:
                membership = (
                    TenantMembership.objects
                    .select_for_update()
                    # .select_related("role")
                    .get(
                        id=membership_id,
                        tenant_id=tenant_id,
                    )
                )
            except TenantMembership.DoesNotExist as exc:
                raise ResourceNotFoundError(
                    "Tenant membership not found."
                ) from exc

            if membership.status in {
                TenantMembership.Status.REMOVED,
            }:
                raise ValidationError(
                    "Cannot assign a role to a removed membership."
                )

            try:
                role = Role.objects.get(
                    id=role_id,
                )
            except Role.DoesNotExist as exc:
                raise ResourceNotFoundError(
                    "Role not found."
                ) from exc

            TenantMembershipRoleService._validate_role(
                tenant_id=tenant_id,
                role=role,
            )

            membership.role = role

            membership.save(
                update_fields=[
                    "role",
                    "updated_at",
                ]
            )

            return membership

    @staticmethod
    @transaction.atomic
    def change_role(
        *,
        tenant_id,
        membership_id,
        role_id,
    ):
        """
        Change an existing membership's role.

        This is intentionally separate from assign_role()
        so callers can express the operation explicitly.
        """

        return TenantMembershipRoleService.assign_role(
            tenant_id=tenant_id,
            membership_id=membership_id,
            role_id=role_id,
        )

    @staticmethod
    @transaction.atomic
    def remove_role(
        *,
        tenant_id,
        membership_id,
    ):
        """
        Remove the role from a membership.
        """

        try:
            membership = (
                TenantMembership.objects
                .select_for_update()
                .get(
                    id=membership_id,
                    tenant_id=tenant_id,
                )
            )
        except TenantMembership.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Tenant membership not found."
            ) from exc

        membership.role = None

        membership.save(
            update_fields=[
                "role",
                "updated_at",
            ]
        )

        return membership

    @staticmethod
    def get_membership_role(
        *,
        tenant_id,
        membership_id,
    ):
        """
        Return the current role assigned to a membership.
        """

        try:
            membership = (
                TenantMembership.objects
                .select_related("role")
                .get(
                    id=membership_id,
                    tenant_id=tenant_id,
                )
            )
        except TenantMembership.DoesNotExist as exc:
            raise ResourceNotFoundError(
                "Tenant membership not found."
            ) from exc

        return membership.role

    @staticmethod
    def _validate_role(role, tenant_id):
        if role.scope != Role.Scope.TENANT:
            raise ValidationError(
                "Platform roles cannot be assigned to tenant memberships."
            )

        if role.tenant_id != tenant_id:
            raise ResourceNotFoundError(
                "Role not found."
            )