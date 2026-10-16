import uuid 
from django.db import models
from django.db.models import Q

class BillingEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    event_type = models.CharField(
        max_length=100,
    )
    aggregate_type = models.CharField(
        max_length=100,
    )
    aggregate_id = models.CharField(
        max_length=100,
    )
    tenant_id = models.UUIDField()
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempts = models.PositiveIntegerField(
        default=0,
    )
    next_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_error = models.CharField(
        max_length=500,
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
                fields=["status", "next_attempt_at"],
                name="bill_event_retry_idx",
            ),
            models.Index(
                fields=["tenant_id", "created_at"],
                name="bill_event_tenant_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type}:{self.id}"
    
class BillingEventDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    event = models.ForeignKey(
        BillingEvent,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    destination = models.CharField(
        max_length=30,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempts = models.PositiveIntegerField(
        default=0,
    )
    next_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_error = models.CharField(
        max_length=500,
        blank=True,
    )
    delivered_at = models.DateTimeField(
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
        constraints = [
            models.UniqueConstraint(
                fields=["event", "destination"],
                name="unique_bill_event_destination",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "next_attempt_at"],
                name="bill_delivery_retry_idx",
            ),
        ]

    def __str__(self):
        return f"{self.destination}:{self.event_id}"