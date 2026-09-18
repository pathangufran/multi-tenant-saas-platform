from uuid import UUID
from django.utils.text import slugify
from django.db import IntegrityError,transaction
from .models import Tenant,TenantMembership
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from django.http import JsonResponse

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
            )
            TenantMembership.objects.create(
                tenant=tenant,
                user_id=owner_user_id,
                status=TenantMembership.Status.ACTIVE,
            )
            
            return tenant
            
        except IntegrityError:
            raise ValueError(
                "A tenant with this slug already exists."
            )
            
    @staticmethod
    def get_user_tenants(*,user_id: UUID) -> list[dict]:
        
        return (
            Tenant.objects
            .filter(
                user_id=user_id,
                membership__status=(
                    TenantMembership.Status.ACTIVE
                )
            )
        )
        
    @staticmethod
    def get_user_tenant(
        *,
        user_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        
        try:
            tenant = (
                Tenant.objects
                .filter(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    membership__status=(
                        TenantMembership.Status.ACTIVE
                    )
                )
            )
            
            return tenant
        
        except Tenant.DoesNotExist:
            raise ResourceNotFoundError(
                message="Tenant not found."
            )