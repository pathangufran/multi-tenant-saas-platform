from django.contrib import admin
from .models import Team

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "name",
        "created_by",
        "created_at",
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