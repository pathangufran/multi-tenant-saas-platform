from django.urls import path
from .views import (
    TenantCreateView,
    TenantListView,
    CurrentTenantView,
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
]