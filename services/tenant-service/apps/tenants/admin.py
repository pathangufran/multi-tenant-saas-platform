from django.contrib import admin
from .models import (
    Tenant,TenantMembership,AuditEvent
)

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "status",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
    )

    list_filter = (
        "status",
    )

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

    search_fields = (
        "user_id",
        "tenant__name",
    )

    list_filter = (
        "status",
    )

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant_id",
        "actor_user_id",
        "event_type",
        "entity_type",
        "entity_id",
        "created_at",
    )

    search_fields = (
        "tenant_id",
        "actor_user_id",
        "entity_id",
    )

    list_filter = (
        "event_type",
        "entity_type",
    )

    readonly_fields = (
        "id",
        "tenant_id",
        "actor_user_id",
        "event_type",
        "entity_type",
        "entity_id",
        "metadata",
        "created_at",
    )