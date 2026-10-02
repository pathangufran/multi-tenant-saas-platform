import uuid 
from django.db import models

class Tag(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    name = models.CharField(
        max_length=100,
    )
    created_by = models.UUIDField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "tags"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="tag_tenant_name_unique",
            ),
        ]

        indexes = [
            models.Index(
                fields=["tenant_id", "name"],
                name="tag_tenant_name_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_by"],
                name="tag_tenant_user_idx",
            ),
        ]

    def __str__(self):
        return self.name
    
class TaskTag(models.Model):
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
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="task_tags",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    class Meta:
        db_table = "task_tags"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tenant_id",
                    "task_id",
                    "tag",
                ],
                name="task_tag_unique",
            ),
        ]

        indexes = [
            models.Index(
                fields=["tenant_id", "task_id"],
                name="tasktag_tenant_task_idx",
            ),
            models.Index(
                fields=["tenant_id", "tag"],
                name="tasktag_tenant_tag_idx",
            ),
        ]

    def __str__(self):
        return f"{self.task_id} - {self.tag.name}"
    