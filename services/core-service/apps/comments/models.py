import uuid 
from django.db import models

class Comment(models.Model):
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
    content = models.TextField()
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
        db_table = "comments"
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["tenant_id", "task_id"],
                name="comment_tenant_task_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_by"],
                name="comment_tenant_user_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_at"],
                name="comment_tenant_created_idx",
            ),
        ]

    def __str__(self):
        return f"Comment {self.id}"