from django.contrib import admin
from .models import OutboxEvent

@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):

    list_display = (
        "event_id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "status",
        "attempts",
        "created_at",
        "published_at",
    )
    list_filter = (
        "status",
        "event_type",
        "producer",
    )
    search_fields = (
        "event_id",
        "event_type",
        "aggregate_id",
    )
    readonly_fields = (
        "event_id",
        "event_type",
        "event_version",
        "producer",
        "tenant_id",
        "aggregate_type",
        "aggregate_id",
        "aggregate_version",
        "correlation_id",
        "causation_id",
        "traceparent",
        "data",
        "status",
        "attempts",
        "available_at",
        "locked_until",
        "lock_token",
        "last_error",
        "published_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False