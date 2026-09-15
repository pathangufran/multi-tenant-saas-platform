from django.db import IntegrityError,transaction
from django.utils.text import slugify
from .models import Tenant

class TenantService:
    
    @staticmethod
    @transaction.atomic
    def create_tenant(
        *,
        name: str,
        slug: str,
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
            return Tenant.objects.create(
                name=name,slug=slug,
            )
            
        except IntegrityError:
            raise ValueError(
                "A tenant with this slug already exists."
            )