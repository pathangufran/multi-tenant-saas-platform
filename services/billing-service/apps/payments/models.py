import uuid
from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.invoices.models import Invoice

class Payment(models.Model):
    class Provider(models.TextChoices):
        MOCK = "MOCK", "Mock Provider"

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"
        REFUNDED = "REFUNDED", "Refunded"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.MOCK,
    )
    provider_payment_id = models.CharField(
        max_length=255,
        blank=True,
    )
    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIATED,
    )
    checkout_url = models.URLField(
        max_length=1000,
        blank=True,
    )
    failure_reason = models.CharField(
        max_length=500,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="payment_amount_nonnegative",
            ),
            models.UniqueConstraint(
                fields=["provider", "provider_payment_id"],
                condition=~Q(provider_payment_id=""),
                name="unique_provider_payment_id",
            ),
        ]
        indexes = [
            models.Index(
                fields=["invoice", "status"],
                name="payment_invoice_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="payment_status_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.id} - {self.status}"

    def mark_failed(self, reason):
        self.status = self.Status.FAILED
        self.failure_reason = str(reason)[:500]
        self.completed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "failure_reason",
                "completed_at",
                "updated_at",
            ]
        )