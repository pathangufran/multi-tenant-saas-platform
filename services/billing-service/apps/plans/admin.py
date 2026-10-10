from django.contrib import admin
from apps.plans.models import Plan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "price",
        "currency",
        "billing_interval",
        "is_active",
        "is_public",
    )
    list_filter = (
        "is_active", 
        "is_public", 
        "billing_interval", 
        "currency"
    )
    search_fields = (
        "code", "name"
    )
    readonly_fields = (
        "id", 
        "created_at",
        "updated_at"
    )
    ordering = (
        "price","name"
    )