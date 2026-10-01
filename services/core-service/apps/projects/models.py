import uuid 
from django.db import models

class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    name = models.CharField(
        max_length=255,
    )
    description = models.TextField(
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.UUIDField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "projects"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="project_tenant_status_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_at"],
                name="project_tenant_created_idx",
            ),
        ]

    def __str__(self):
        return self.name