from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "project_id",
        "title",
        "priority",
        "status",
        "assignee_id",
        "due_date",
        "created_at",
    )
    list_filter = (
        "priority",
        "status",
    )
    search_fields = (
        "title",
        "description",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )