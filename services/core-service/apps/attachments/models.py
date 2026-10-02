import uuid 
from django.db import models

class Attachment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    task_id = models.UUIDField(
        db_index=True,
    )
    s3_key = models.CharField(
        max_length=1024,
    )
    filename = models.CharField(
        max_length=255,
    )
    content_type = models.CharField(
        max_length=255,
    )
    size = models.PositiveIntegerField()
    created_by = models.UUIDField(
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "attachments"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["tenant_id", "task_id"],
                name="attachment_tenant_task_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_by"],
                name="attachment_tenant_user_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_at"],
                name="attachment_tenant_created_idx",
            ),
        ]

    def __str__(self):
        return self.filename