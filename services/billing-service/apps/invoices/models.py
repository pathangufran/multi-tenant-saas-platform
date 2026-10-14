import uuid 
from django.db import models
from django.db.models import Q
from apps.subscriptions.models import Subscription

class Invoice(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"
        UNCOLLECTIBLE = "UNCOLLECTIBLE", "Uncollectible"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    invoice_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    plan_code = models.CharField(
        max_length=50,
    )
    plan_name = models.CharField(
        max_length=100,
    )
    currency = models.CharField(
        max_length=3,
    )
    billing_interval = models.CharField(
        max_length=10,
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )    
    issued_at = models.DateTimeField()
    due_at = models.DateTimeField()
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    voided_at = models.DateTimeField(
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
        db_table = "billing_invoices"
        ordering = ["-issued_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="invoice_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(tax_amount__gte=0),
                name="invoice_tax_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="invoice_total_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(period_end__gt=models.F("period_start")),
                name="invoice_period_valid",
            ),
            models.CheckConstraint(
                condition=Q(due_at__gte=models.F("issued_at")),
                name="invoice_due_after_issue",
            ),
            models.UniqueConstraint(
                fields=["subscription", "period_start", "period_end"],
                name="invoice_subscription_period_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="invoice_tenant_status_idx",
            ),
            models.Index(
                fields=["status", "due_at"],
                name="invoice_status_due_idx",
            ),
        ]

    def __str__(self):
        return self.invoice_number
    
class InvoiceLineItem(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    description = models.CharField(
        max_length=255,
    )
    quantity = models.PositiveIntegerField(
        default=1,
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "billing_invoice_line_items"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="invoice_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="invoice_item_unit_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="invoice_item_amount_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.invoice.invoice_number}: {self.description}"