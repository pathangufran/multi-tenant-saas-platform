from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "task_id",
        "created_by",
        "created_at",
    )
    list_filter = (
        "created_at",
    )
    search_fields = (
        "id",
        "content",
        "task_id",
        "created_by",
        "tenant_id",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )