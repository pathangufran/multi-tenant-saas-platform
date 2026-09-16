from django.db import models
from .querysets import TenantScopedQuerySet

class TenantScopedModel(models.Model):
    
    objects = TenantScopedQuerySet.as_manager()
    
    class Meta:
        abstract = True