from django.contrib import admin
from apps.subscriptions.models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "plan",
        "status",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
    )
    list_filter = ("status", "cancel_at_period_end")
    search_fields = (
        "id",
        "tenant_id",
        "external_subscription_id",
        "plan__code",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "canceled_at",
        "ended_at",
    )
    ordering = ("-created_at",)