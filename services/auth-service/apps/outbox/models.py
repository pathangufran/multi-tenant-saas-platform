import uuid
from django.db import models
from django.utils import timezone

class OutboxEvent(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PUBLISHED = "PUBLISHED", "Published"

    event_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    event_type = models.CharField(
        max_length=150,
        db_index=True,
    )
    event_version = models.PositiveIntegerField(
        default=1,
    )
    producer = models.CharField(
        max_length=100,
        default="auth-service",
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
    aggregate_version = models.PositiveIntegerField()
    correlation_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
    )
    causation_id = models.UUIDField(
        null=True,
        blank=True,
    )
    traceparent = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    data = models.JSONField(
        default=dict,
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
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["status", "available_at"],
                name="auth_outbox_status_avail_idx",
            ),
            models.Index(
                fields=[
                    "tenant_id",
                    "aggregate_type",
                    "aggregate_id",
                ],
                name="auth_outbox_aggregate_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"