from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "status",
        "created_at",
        "updated_at",
    )

    list_filter = ("status",)
    
    search_fields = ("name","slug",)
    
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)