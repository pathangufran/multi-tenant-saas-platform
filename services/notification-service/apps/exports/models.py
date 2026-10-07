import uuid 
from django.db import models

class Export(models.Model):
    class ExportType(models.TextChoices):
        PROJECTS = "PROJECTS", "Projects"
        USERS = "USERS", "Users"
        TASKS = "TASKS", "Tasks"
        AUDIT_LOGS = "AUDIT_LOGS", "Audit Logs"
        
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    requested_by = models.UUIDField(
        db_index=True,
    )
    export_type = models.CharField(
        max_length=30,
        choices=ExportType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
    )
    storage_key = models.CharField(
        max_length=500,
        blank=True,
    )
    row_count = models.PositiveIntegerField(
        default=0,
    )
    error_message = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "exports_export"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "tenant_id","status",
                ],
                name="export_tenant_status_idx",
            ),
            models.Index(
                fields=[
                    "tenant_id","export_type",
                ],
                name="export_tenant_type_idx",
            ),
            models.Index(
                fields=[
                    "tenant_id","created_at",
                ],
                name="export_tenant_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.export_type} "
            f"{self.id} "
            f"({self.status})"
        )