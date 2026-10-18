import uuid
from django.db import models
from django.db.models import Q
from apps.plans.models import Plan

class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "TRIALING", "Trialing"
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past due"
        CANCELED = "CANCELED", "Canceled"
        EXPIRED = "EXPIRED", "Expired"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,        
    )
    start_at = models.DateTimeField()
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(
        default=False,
    )
    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    ended_at = models.DateTimeField(
        null=True, 
        blank=True,
    )
    external_subscription_id = models.CharField(
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "billing_subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="sub_tenant_status_idx",
            ),
            models.Index(
                fields=["status", "current_period_end"],
                name="sub_status_period_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    current_period_end__gt=models.F("current_period_start"),
                ),
                name="sub_period_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["tenant_id"],
                condition=Q(
                    status__in=["TRIALING", "ACTIVE", "PAST_DUE"]
                ),
                name="sub_one_open_per_tenant",
            ),
            models.UniqueConstraint(
                fields=["external_subscription_id"],
                condition=~Q(external_subscription_id=""),
                name="sub_external_id_unique",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_id} - {self.plan.code} ({self.status})"