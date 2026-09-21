import uuid 
from django.db import models 
from django.db.models import Q
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
    role = models.ForeignKey(
        "Role",
        on_delete=models.PROTECT,
        related_name="memberships",
        null=True,
        blank=True,
    )
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
                fields=["tenant", "status","role"],
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
        role_code = (
            self.role.code
            if self.role
            else "NO_ROLE"
        )
        return f"{self.user_id} - {self.tenant.name} - {role_code}" 
    
class AuditEvent(models.Model):
    class EventType(models.TextChoices):
        TENANT_CREATED = (
            "tenant.created",
            "Tenant Created",
        )
        TENANT_UPDATED = (
            "tenant.updated",
            "Tenant Updated",
        )
        TENANT_SUSPENDED = (
            "tenant.suspended",
            "Tenant Suspended",
        )
        TENANT_ACTIVATED = (
            "tenant.activated",
            "Tenant Activated",
        )
        TENANT_DEACTIVATED = (
            "tenant.deactivated",
            "Tenant Deactivated",
        )
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    actor_user_id = models.UUIDField(
        db_index=True,
    )
    event_type = models.CharField(
        max_length=100,
        choices=EventType.choices,
        db_index=True,
    )
    entity_type = models.CharField(
        max_length=100,
    )
    entity_id = models.UUIDField(
        db_index=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=[
                    "tenant_id","created_at",
                ],
                name="audit_tenant_created_idx",
            ),
            models.Index(
                fields=[
                    "tenant_id","event_type",
                ],
                name="audit_tenant_event_idx",
            ),
            models.Index(
                fields=[
                    "actor_user_id","created_at",
                ],
                name="audit_actor_created_idx",
            ),
        ]
        
    def __str__(self):
        return (
            f"{self.event_type} - "
            f"{self.entity_id}"
        )
        
class Permission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=255,
    )
    code = models.CharField(
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        ordering = ["code"]
        
    def __str__(self):
        return self.code
    
class Role(models.Model):
    class Scope(models.TextChoices):
        TENANT = "tenant", "Tenant"
        PLATFORM = "platform", "Platform"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=100,
    )
    code = models.CharField(
        max_length=100,
    )
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.TENANT,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
    )
    description = models.TextField(
        blank=True,
    )
    is_system_role = models.BooleanField(
        default=False,
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        ordering = ["scope", "code"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tenant","code",
                ],
                name="role_tenant_code_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        scope="tenant",
                        tenant__isnull=False,
                    )
                    | Q(
                        scope="platform",
                        tenant__isnull=True,
                    )
                ),
                name="role_scope_tenant_consistency",
            ),
        ]

    def __str__(self):
        return self.code