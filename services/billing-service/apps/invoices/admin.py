from django.contrib import admin
from apps.invoices.models import (
    Invoice, 
    InvoiceLineItem
)

class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = (
        "id",
        "description",
        "quantity",
        "unit_price",
        "amount",
        "created_at",
    )
    can_delete = False

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "tenant_id",
        "plan_code",
        "total",
        "currency",
        "status",
        "issued_at",
        "due_at",
    )
    list_filter = ("status", "currency", "billing_interval")
    search_fields = ("invoice_number", "tenant_id", "plan_code")
    readonly_fields = (
        "id",
        "invoice_number",
        "tenant_id",
        "subscription",
        "plan_code",
        "plan_name",
        "currency",
        "billing_interval",
        "period_start",
        "period_end",
        "subtotal",
        "tax_amount",
        "total",
        "status",
        "issued_at",
        "due_at",
        "paid_at",
        "voided_at",
        "created_at",
        "updated_at",
    )
    inlines = [InvoiceLineItemInline]
    ordering = ("-issued_at",)

@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "description",
        "quantity",
        "unit_price",
        "amount",
    )
    search_fields = ("invoice__invoice_number", "description")
    readonly_fields = (
        "id",
        "invoice",
        "description",
        "quantity",
        "unit_price",
        "amount",
        "created_at",
    )