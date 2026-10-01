from django.contrib import admin
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "name",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = (
        "status",
    )
    search_fields = (
        "name",
        "description",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )