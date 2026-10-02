import uuid  
from django.db import models

class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        
    class Status(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    project_id = models.UUIDField(
        db_index=True,
    )
    title = models.CharField(
        max_length=255,
    )
    description = models.TextField(
        blank=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    assignee_id = models.UUIDField(
        null=True,
        blank=True,
    )
    due_date = models.DateField(
        null=True,
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
        db_table = "tasks"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["tenant_id", "project_id"],
                name="task_tenant_project_idx",
            ),
            models.Index(
                fields=["tenant_id", "status"],
                name="task_tenant_status_idx",
            ),
            models.Index(
                fields=["tenant_id", "assignee_id"],
                name="task_tenant_assignee_idx",
            ),
            models.Index(
                fields=["tenant_id", "due_date"],
                name="task_tenant_due_date_idx",
            ),
        ]

    def __str__(self):
        return self.title