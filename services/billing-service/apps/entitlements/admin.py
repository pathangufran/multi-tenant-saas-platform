from django.contrib import admin
from apps.entitlements.models import (
    Feature,
    PlanFeature,
)

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "name",
        "value_type",
        "is_active",
    )
    list_filter = (
        "value_type",
        "is_active",
    )
    search_fields = (
        "key",
        "name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = ("key",)

@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "feature",
        "enabled",
        "value",
        "updated_at",
    )
    list_filter = (
        "enabled",
        "feature__value_type",
    )
    search_fields = (
        "plan__code",
        "feature__key",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_select_related = (
        "plan",
        "feature",
    )