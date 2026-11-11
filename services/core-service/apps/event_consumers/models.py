import uuid 
from django.db import models
from django.utils import timezone

class ProcessedEvent(models.Model):
    class Status(models.TextChoices):
        PROCESSED = "PROCESSED", "Processed"
        IGNORED = "IGNORED", "Ignored"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    event_id = models.UUIDField(
        unique=True,
        db_index=True,
    )
    event_type = models.CharField(
        max_length=150,
        db_index=True,
    )
    event_version = models.PositiveIntegerField()
    producer = models.CharField(
        max_length=100,
    )
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    payload = models.JSONField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSED,
    )
    processed_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        db_table = "core_processed_events"

        ordering = ["-processed_at"]

        indexes = [
            models.Index(
                fields=["event_type", "processed_at"],
                name="core_evt_type_proc_idx",
            ),
            models.Index(
                fields=["tenant_id", "processed_at"],
                name="core_evt_tenant_proc_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"
        
class FailedEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    event_id = models.UUIDField(
        db_index=True,
    )
    event_type = models.CharField(
        max_length=150,
        default="unknown",
    )
    topic = models.CharField(
        max_length=255,
    )
    partition = models.PositiveIntegerField()
    offset = models.PositiveBigIntegerField()
    attempts = models.PositiveIntegerField(
        default=0,
    )
    error_message = models.TextField(
        blank=True,
        default="",
    )
    original_payload = models.JSONField(
        default=dict,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    dlq_published_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "core_failed_events"

        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "event_id",
                    "topic",
                    "partition",
                    "offset",
                ],
                name="core_failed_event_source_unique",
            ),
        ]

        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="core_failed_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.event_type} - "
            f"{self.event_id} - {self.status}"
        )
    
class TenantStatusProjection(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        DEACTIVATED = "DEACTIVATED", "Deactivated"
        
    tenant_id = models.UUIDField(
        primary_key=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "core_tenant_status_projection"
        
        ordering = ["tenant_id"]
        
    def __str__(self):
        return f"{self.tenant_id} - {self.status}"