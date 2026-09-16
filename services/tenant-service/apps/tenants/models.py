import uuid 
from django.db import models 
from django.db.models.functions import Lower
from .mixins import TenantScopedModel

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
    
class TenantMembership(TenantScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user_id = models.UUIDField(db_index=True,)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
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
            models.Index(
                fields=["tenant", "status"],
                name="membership_tenant_status_idx",
            ),
            models.Index(
                fields=["user_id", "status"],
                name="membership_user_status_idx",
            ),
            models.Index(
                fields=["joined_at","created_at"],
                name="membership_jd_at_cd_at_idx"
            )
        ]
        
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user_id"],
                name="tenant_membership_tenant_user_unique",
            ),
        ]
        
    def __str__(self):
        return f"{self.user_id} - {self.tenant.name}"