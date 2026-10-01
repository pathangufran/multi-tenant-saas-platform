import uuid 
from django.db import models

class Team(models.Model):
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
    created_by = models.UUIDField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "teams"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="team_tenant_name_unique",
            ),
        ]

        indexes = [
            models.Index(
                fields=["tenant_id", "created_at"],
                name="team_tenant_created_idx",
            ),
        ]

    def __str__(self):
        return self.name