import uuid
from django.db import models
from django.db.models import Q

class UsageRecord(models.Model):
    class Metric(models.TextChoices):
        ACTIVE_USERS = "ACTIVE_USERS", "Active users"
        PROJECTS = "PROJECTS", "Projects"
        STORAGE_BYTES = "STORAGE_BYTES", "Storage bytes"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    metric = models.CharField(
        max_length=20,
        choices=Metric.choices,
    )
    quantity = models.BigIntegerField(default=0)
    source = models.CharField(
        max_length=64,
        default="manual",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "billing_usage_records"
        ordering = ["metric"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "metric"],
                name="usage_tenant_metric_unique",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="usage_quantity_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "metric"],
                name="usage_tenant_metric_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_id} - {self.metric}: {self.quantity}"