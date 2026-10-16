from django.contrib import admin
from apps.integrations.models import (
    BillingEvent,
    BillingEventDelivery,
)

class BillingEventDeliveryInline(admin.TabularInline):
    model = BillingEventDelivery
    extra = 0
    can_delete = False
    readonly_fields = (
        "id",
        "destination",
        "status",
        "attempts",
        "next_attempt_at",
        "last_error",
        "delivered_at",
        "created_at",
        "updated_at",
    )


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "tenant_id",
        "status",
        "attempts",
        "created_at",
    )
    list_filter = ("status", "event_type")
    search_fields = ("id", "aggregate_id", "tenant_id")
    readonly_fields = (
        "id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "tenant_id",
        "payload",
        "status",
        "attempts",
        "next_attempt_at",
        "last_error",
        "created_at",
        "updated_at",
    )
    inlines = [BillingEventDeliveryInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(BillingEventDelivery)
class BillingEventDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "destination",
        "status",
        "attempts",
        "delivered_at",
    )
    list_filter = ("destination", "status")
    readonly_fields = (
        "id",
        "event",
        "destination",
        "status",
        "attempts",
        "next_attempt_at",
        "last_error",
        "delivered_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False