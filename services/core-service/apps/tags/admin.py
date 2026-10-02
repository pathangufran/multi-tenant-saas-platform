from django.contrib import admin
from .models import Tag, TaskTag

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "name",
        "created_by",
        "created_at",
    )
    search_fields = (
        "id",
        "name",
        "tenant_id",
        "created_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

@admin.register(TaskTag)
class TaskTagAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "task_id",
        "tag",
        "created_at",
    )
    search_fields = (
        "id",
        "task_id",
        "tenant_id",
        "tag__name",
    )
    readonly_fields = (
        "id",
        "created_at",
    )