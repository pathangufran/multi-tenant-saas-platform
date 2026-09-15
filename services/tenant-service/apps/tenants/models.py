import uuid 
from django.db import models 
from django.db.models.functions import Lower

class Tenant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DEACTIVATED = "deactivated", "Deactivated"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255,)
    slug = models.SlugField(
        max_length=100,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(auto_now=True,)
    
    class Meta:
        ordering = ["-created_at"]
        
        indexes = [
            models.Index(fields=["id"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        
        constraints = [
            models.UniqueConstraint(
                Lower("slug"),
                name="tenant_slug_ci_unique",
            )
        ]
        
    def __str__(self):
        return self.name
    