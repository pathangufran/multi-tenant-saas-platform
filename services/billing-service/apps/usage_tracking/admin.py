from django.contrib import admin
from .models import UsageRecord

@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        "tenant_id",
        "metric",
        "quantity",
        "source",
        "updated_at",
    )
    list_filter = (
        "metric",
        "source",
    )
    search_fields = ("tenant_id",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    ordering = (
        "tenant_id",
        "metric",
    )