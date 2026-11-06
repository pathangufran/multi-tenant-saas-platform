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