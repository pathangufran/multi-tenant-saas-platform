from django.contrib import admin
from apps.payments.models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice",
        "provider",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("provider", "status", "currency")
    search_fields = (
        "id",
        "provider_payment_id",
        "idempotency_key",
        "invoice__invoice_number",
    )
    readonly_fields = (
        "id",
        "invoice",
        "provider",
        "provider_payment_id",
        "idempotency_key",
        "amount",
        "currency",
        "status",
        "checkout_url",
        "failure_reason",
        "created_at",
        "updated_at",
        "completed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False