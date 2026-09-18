from django.urls import path
from .views import (
    TenantCreateView,
    TenantListView,
    CurrentTenantView,
    TenantActivateView,
    TenantDeactivateView,
    TenantSuspendView,
)

urlpatterns = [
    path(
        "", 
        TenantCreateView.as_view(), 
        name="tenant-create"
    ),
    path(
        "list/",
        TenantListView.as_view(),
        name="tenant-list",
    ),
    path(
        "<uuid:tenant_id>/",
        CurrentTenantView.as_view(),
        name="current-tenant",
    ),
    path(
        "<uuid:tenant_id>/suspend/",
        TenantSuspendView.as_view(),
        name="tenant-suspend",
    ),
    path(
        "<uuid:tenant_id>/activate/",
        TenantActivateView.as_view(),
        name="tenant-activate",
    ),
    path(
        "<uuid:tenant_id>/deactivate/",
        TenantDeactivateView.as_view(),
        name="tenant-deactivate",
    ),
]