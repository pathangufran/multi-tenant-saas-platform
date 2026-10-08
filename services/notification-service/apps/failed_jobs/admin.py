from django.contrib import admin
from .models import FailedJobs

@admin.register(FailedJobs)
class FailedJobAdmin(admin.ModelAdmin):

    list_display = (
        "task_name",
        "task_id",
        "status",
        "retry_count",
        "tenant_id",
        "exception_type",
        "created_at",
        "resolved_at",
    )
    list_filter = (
        "status",
        "task_name",
        "created_at",
    )
    search_fields = (
        "task_id",
        "task_name",
        "tenant_id",
        "user_id",
        "request_id",
        "error_message",
    )
    readonly_fields = (
        "id",
        "task_id",
        "task_name",
        "tenant_id",
        "user_id",
        "request_id",
        "status",
        "retry_count",
        "exception_type",
        "error_message",
        "traceback",
        "task_args",
        "task_kwargs",
        "metadata",
        "created_at",
        "resolved_at",
    )
    ordering = (
        "-created_at",
    )