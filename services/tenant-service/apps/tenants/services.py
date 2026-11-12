from uuid import UUID
from django.utils.text import slugify
from django.db import IntegrityError,transaction
from .models import Tenant,TenantMembership,AuditEvent
from apps.common.exceptions import (
    ResourceNotFoundError,
)
from django.http import JsonResponse
from .audit_service import AuditEventService
from apps.outbox.services import OutboxService

class TenantService:
    
    @staticmethod
    @transaction.atomic
    def create_tenant(
        *,
        name: str,
        slug: str,
        owner_user_id,
    ) -> Tenant:
        name = name.strip()
        slug = slugify(slug)
        
        if not name:
            raise ValueError(
                "Tenant name is required."
            )
        if not slug:
            raise ValueError(
                "Tenant slug is required."
            )
        
        if Tenant.objects.filter(
            slug__iexact=slug,
        ).exists():
            raise ValueError(
                "A tenant with this slug already exists."
            )
            
        try:
            tenant = Tenant.objects.create(
                name=name,
                slug=slug,
                status=Tenant.Status.ACTIVE,
                aggregate_version=1,
            )
            owner_membership = TenantMembership.objects.create(
                tenant=tenant,
                user_id=owner_user_id,
                status=TenantMembership.Status.ACTIVE,
            )
            AuditEventService.record_tenant_event(
                tenant_id=tenant.id,
                actor_user_id=owner_user_id,
                event_type=(
                    AuditEvent.EventType.TENANT_CREATED
                ),
                metadata={
                    "name": tenant.name,
                    "slug": tenant.slug,
                },
            )
            
            OutboxService.record_event(
                event_type="tenant.created",
                event_version=1,
                tenant_id=tenant.id,
                aggregate_type="tenant",
                aggregate_id=tenant.id,
                aggregate_version=tenant.aggregate_version,
                data={
                    "tenant_id": str(tenant.id),
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "owner_user_id": str(owner_user_id),
                },
            )
            
            OutboxService.record_event(
                event_type="member.joined",
                aggregate_type="membership",
                aggregate_id=owner_membership.id,
                tenant_id=tenant.id,
                aggregate_version=1,
                data={
                    "membership_id": str(owner_membership.id),
                    "tenant_id": str(tenant.id),
                    "user_id": str(owner_user_id),
                    "role_id": None,
                },
            )
            
            return tenant
            
        except IntegrityError:
            raise ValueError(
                "A tenant with this slug already exists."
            )
            
    @staticmethod
    def get_user_tenants(*,user_id: UUID) -> Tenant:
        
        return (
            Tenant.objects
            .filter(
                memberships__user_id=user_id,
                memberships__status=(
                    TenantMembership.Status.ACTIVE,
                )
            )
            .distinct()
        )
        
    @staticmethod
    def get_user_tenant(
        *,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Tenant:
        
        try:
            tenant = (
                Tenant.objects
                .get(
                    id=tenant_id,
                    memberships__user_id=user_id,
                    memberships__status=(
                        TenantMembership.Status.ACTIVE
                    )
                )
            )
            
            return tenant
        
        except Tenant.DoesNotExist:
            raise ResourceNotFoundError(
                message="Tenant not found."
            )
            
    @staticmethod
    @transaction.atomic
    def update_tenant(
        *,
        tenant_id,
        user_id,
        name=None,
        slug=None,
    ) -> Tenant:
        
        try:
            tenant = (
                Tenant.objects
                .select_for_update()
                .get(
                    id=tenant_id,
                    memberships__user_id=user_id,
                    memberships__status=(
                        TenantMembership.Status.ACTIVE
                    )
                )
            )
        except Tenant.DoesNotExist:
            raise ResourceNotFoundError(
                message="Tenant not found."
            )
            
        old_name = tenant.name
        old_slug = tenant.slug
            
        if name is not None:
            name = name.strip()
            
            if not name:
                raise ValueError(
                    "Tenant name cannot be empty."
                )
                
            tenant.name = name
            
        if slug is not None:
            slug = slugify(slug)
            
            if not slug:
                raise ValueError(
                    "Tenant slug cannot be empty."
                )
                
            duplicate_exists = (
                Tenant.objects
                .filter(slug__iexact=slug)
                .exclude(id=tenant.id)
                .exists()
            )
            
            if duplicate_exists:
                raise ValueError(
                    "A tenant with this slug already exists."
                )
                
            tenant.slug = slug
            
        try:
            tenant.aggregate_version += 1
            
            tenant.save(
                update_fields=[
                    "name",
                    "slug",
                    "aggregate_version",
                    "updated_at",
                ]
            )
        except IntegrityError:
            raise ValueError(
                "A tenant with this slug already exists."
            )
            
        AuditEventService.record_tenant_event(
            tenant_id=tenant.id,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_UPDATED
            ),
            metadata={
                "previous_name": old_name,
                "new_name": tenant.name,
                "previous_slug": old_slug,
                "new_slug": tenant.slug,
            },
        )
            
        return tenant
            
    @staticmethod
    @transaction.atomic
    def change_status(
        *,
        tenant_id,
        user_id,
        status,
    ) -> Tenant:
        
        try:
            tenant = (
                Tenant.objects
                .select_for_update()
                .get(
                    id=tenant_id,
                    memberships__user_id=user_id,
                    memberships__status=(
                        TenantMembership.Status.ACTIVE
                    )
                )
            )
        except Tenant.DoesNotExist:
            raise ResourceNotFoundError(
                message="Tenant not found."
            )
        
        new_status = status
        
        if tenant.status == new_status:
            return tenant

        tenant.status = new_status
        tenant.aggregate_version += 1

        tenant.save(
            update_fields=[
                "status",
                "aggregate_version",
                "updated_at",
            ]
        )
        
        event_map = {
            Tenant.Status.SUSPENDED: (
                AuditEvent.EventType.TENANT_SUSPENDED
            ),
            Tenant.Status.ACTIVE: (
                AuditEvent.EventType.TENANT_ACTIVATED
            ),
            Tenant.Status.DEACTIVATED: (
                AuditEvent.EventType.TENANT_DEACTIVATED
            ),
        }
        
        event_type = event_map.get(new_status)
        
        if event_type:
            TenantService._record_lifecycle_event(
                tenant=tenant,
                event_type=event_type,
            )
        
        AuditEventService.record_tenant_event(
            tenant_id=tenant.id,
            actor_user_id=user_id,
            event_type=event_type,
            metadata={
                "new_status": tenant.status,
            },
        )
        
        return tenant
            
    @staticmethod
    @transaction.atomic
    def suspend_tenant(
        *,
        tenant_id,
        user_id,
    ) -> Tenant:
        
        return TenantService.change_status(
            tenant_id=tenant_id,
            user_id=user_id,
            status=Tenant.Status.SUSPENDED,
        )
        
    @staticmethod
    @transaction.atomic
    def activate_tenant(
        *,
        tenant_id,
        user_id,
    ) -> Tenant:
        
        return TenantService.change_status(
            tenant_id=tenant_id,
            user_id=user_id,
            status=Tenant.Status.ACTIVE,
        )
        
    @staticmethod
    @transaction.atomic
    def deactivate_tenant(
        *,
        tenant_id,
        user_id,
    ) -> Tenant:
        
        return TenantService.change_status(
            tenant_id=tenant_id,
            user_id=user_id,
            status=Tenant.Status.DEACTIVATED,
        )
        
    @staticmethod
    def _record_lifecycle_event(
        tenant,
        event_type,
        actor_user_id=None,
    ):

        OutboxService.record_event(
            event_type=event_type,
            event_version=1,
            tenant_id=tenant.id,
            aggregate_type="tenant",
            aggregate_id=tenant.id,
            aggregate_version=tenant.aggregate_version,
            data={
                "tenant_id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "status": tenant.status,
                "actor_user_id": (
                    str(actor_user_id)
                    if actor_user_id else None
                ),
            },
        )