from django.contrib import admin
from .models import FailedEvent
from .models import ProcessedEvent

@admin.register(ProcessedEvent)
class ProcessedEventAdmin(admin.ModelAdmin):

    list_display = (
        "event_id",
        "event_type",
        "producer",
        "tenant_id",
        "status",
        "processed_at",
    )
    list_filter = (
        "status",
        "event_type",
        "producer",
    )
    search_fields = (
        "event_id",
        "event_type",
        "producer",
    )
    readonly_fields = (
        "id",
        "event_id",
        "event_type",
        "event_version",
        "producer",
        "tenant_id",
        "payload",
        "status",
        "processed_at",
    )

    ordering = ("-processed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(FailedEvent)
class FailedEventAdmin(admin.ModelAdmin):

    list_display = (
        "event_id",
        "event_type",
        "topic",
        "partition",
        "offset",
        "attempts",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "event_type",
        "topic",
    )

    search_fields = (
        "event_id",
        "event_type",
        "error_message",
    )

    readonly_fields = (
        "id",
        "event_id",
        "event_type",
        "topic",
        "partition",
        "offset",
        "attempts",
        "error_message",
        "original_payload",
        "status",
        "dlq_published_at",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False