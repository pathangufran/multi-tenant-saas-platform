from django.contrib import admin
from .models import Attachment

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "task_id",
        "filename",
        "content_type",
        "size",
        "created_by",
        "created_at",
    )
    list_filter = (
        "content_type",
        "created_at",
    )
    search_fields = (
        "id",
        "filename",
        "s3_key",
        "tenant_id",
        "task_id",
        "created_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )