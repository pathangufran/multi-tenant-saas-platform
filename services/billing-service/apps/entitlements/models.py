import uuid
from django.db import models
from django.db.models import Q
from apps.plans.models import Plan

class Feature(models.Model):
    class ValueType(models.TextChoices):
        BOOLEAN = "BOOLEAN", "Boolean"
        INTEGER = "INTEGER", "Integer"
        STORAGE_BYTES = "STORAGE_BYTES", "Storage in bytes"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,   
    )
    key  = models.SlugField(
        max_length=100,
        unique=True,
    )
    name = models.CharField(
        max_length=150,
    )
    description = models.TextField(
        blank=True,
    )
    value_type = models.CharField(
        max_length=20,
        choices=ValueType.choices,
    )
    is_active = models.BooleanField(
        default=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    class Meta:
        db_table = "billing_features"
        ordering = ["key"]

    def __str__(self):
        return self.key
    
class PlanFeature(models.Model):
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name="feature_entitlements",
    )
    feature = models.ForeignKey(
        Feature,
        on_delete=models.PROTECT,
        related_name="plan_entitlements",
    )
    enabled = models.BooleanField(
        default=True,
    )
    value = models.JSONField(
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
        db_table = "billing_plan_features"
        ordering = ["feature__key"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "feature"],
                name="plan_feature_unique",
            ),
            models.CheckConstraint(
                condition=Q(enabled=True) | Q(value__isnull=True),
                name="disabled_feature_no_value",
            ),
        ]
        indexes = [
            models.Index(
                fields=["plan", "enabled"],
                name="plan_feature_enabled_idx",
            ),
        ]

    def __str__(self):
        return f"{self.plan.code} - {self.feature.key}"