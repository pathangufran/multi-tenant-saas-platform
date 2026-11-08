import uuid
from django.db import models
from django.utils import timezone

class OutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PUBLISHED = "published", "Published"
        
    event_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    event_type = models.CharField(
        max_length=150,
        db_index=True,
    )
    event_version = models.PositiveSmallIntegerField(
        default=1,
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    producer = models.CharField(
        max_length=100,
        default="tenant-service",
    )
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    aggregate_type = models.CharField(
        max_length=100,
    )
    aggregate_id = models.CharField(
        max_length=255,
    )
    aggregate_version = models.PositiveBigIntegerField(
        default=1,
    )
    correlation_id = models.UUIDField(
        null=True,
        blank=True,
    )
    causation_id = models.UUIDField(
        null=True,
        blank=True,
    )
    traceparent = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    data = models.JSONField(
        default=dict,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.PositiveIntegerField(
        default=0,
    )
    available_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
    )
    lock_token = models.UUIDField(
        null=True,
        blank=True,
    )
    last_error = models.TextField(
        blank=True,
        default="",
    )
    published_at = models.DateTimeField(
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
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["status", "available_at"],
                name="outbox_status_available_idx",
            ),
            models.Index(
                fields=[
                    "aggregate_type",
                    "aggregate_id",
                    "aggregate_version",
                ],
                name="outbox_aggregate_version_idx",
            ),
            models.Index(
                fields=["tenant_id", "status"],
                name="outbox_tenant_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"
