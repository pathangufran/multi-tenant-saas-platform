import uuid 
from django.db import models

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
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSED,
        db_index=True,
    )
    processed_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    class Meta:
        ordering = ["-processed_at"]

        indexes = [
            models.Index(
                fields=["event_type", "processed_at"],
                name="evt_type_processed_idx",
            ),
            models.Index(
                fields=["tenant_id", "processed_at"],
                name="evt_tenant_processed_idx",
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
        db_index=True,
    )
    topic = models.CharField(
        max_length=255,
    )
    partition = models.PositiveIntegerField()
    offset = models.PositiveBigIntegerField()
    attempts = models.PositiveIntegerField(
        default=0,
    )
    error_message = models.TextField()
    original_payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
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
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["event_id", "topic", "partition", "offset"],
                name="failed_event_source_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="failed_evt_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"
