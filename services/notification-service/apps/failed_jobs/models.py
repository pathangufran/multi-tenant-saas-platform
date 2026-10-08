import uuid
from django.db import models

class FailedJobs(models.Model):
    class Status(models.TextChoices):
        FAILED = "FAILED","Failed"
        RESOLVED = "RESOLVED","Resolved"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    task_id = models.UUIDField(
        max_length=255,
        db_index=True,
    )
    task_name = models.CharField(
        max_length=255,
        db_index=True,
    )
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    request_id = models.UUIDField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FAILED,
        db_index=True,
    )
    retry_count = models.PositiveIntegerField(
        default=0,
    )
    exception_type = models.CharField(
        max_length=500,
    )
    error_message = models.TextField()
    traceback = models.TextField(
        blank=True,
    )
    task_args = models.JSONField(
        default=list,
        blank=True,
    )
    task_kwargs = models.JSONField(
        default=dict,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    resolution_notes = models.TextField(
        blank=True,
    )
    
    class Meta:
        db_table = "failed_jobs"
        ordering = ["-created_at",]

        indexes = [
            models.Index(
                fields=[
                    "task_name","status",
                ],
                name="failed_job_task_status_idx",
            ),
            models.Index(
                fields=[
                    "tenant_id","status",
                ],
                name="failed_job_tenant_status_idx",
            ),
            models.Index(
                fields=["created_at",],
                name="failed_job_created_idx",
            ),
        ]

    def __str__(self) -> str:

        return (
            f"{self.task_name} "
            f"({self.task_id})"
        )