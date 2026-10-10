import uuid 
from django.core.validators import MinValueValidator
from django.db import models

class Plan(models.Model):
    class BillingInterval(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"
        
    id = models.UUIDField(
        primary_key=True,   
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=50,
        unique=True,
    )
    name = models.CharField(
        max_length=100,
    )
    description = models.TextField(
        blank=True,
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(
        max_length=3,
        default="INR",
    )
    billing_interval = models.CharField(
        max_length=10,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
    )
    is_active = models.BooleanField(
        default=True
    )
    is_public = models.BooleanField(
        default=True
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = "billing_plans"
        ordering = ["price","name"]
        indexes = [
            models.Index(
                fields=["is_active", "is_public"],
                name="plan_active_public_idx",
            ),
            models.Index(
                fields=["billing_interval", "is_active"],
                name="plan_interval_active_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="plan_price_nonnegative",
            ),
        ]
        
    def __str__(self):
        return f"{self.code} - {self.name}"