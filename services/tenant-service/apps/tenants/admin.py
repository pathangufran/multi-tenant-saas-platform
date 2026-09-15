from django.contrib import admin
from .models import Tenant
from .models import Tenant, TenantMembership

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
    
@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "user_id",
        "status",
        "joined_at",
        "created_at",
    )

    list_filter = ("status",)

    search_fields = (
        "tenant__name",
        "tenant__slug",
        "user_id",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)