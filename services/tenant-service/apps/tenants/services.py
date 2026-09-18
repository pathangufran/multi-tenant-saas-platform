from django.db import IntegrityError,transaction
from django.utils.text import slugify
from .models import Tenant
from .membership_service import TenantMembership

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