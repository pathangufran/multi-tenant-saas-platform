from django.urls import path
from apps.usage_tracking.views import (
    AdminUsageCreateView,
    AdminUsageListView,
    AdminUsageDetailView,
    AdminUsageAdjustmentView,
)

urlpatterns = [
    path(
        "usage/create/",
        AdminUsageCreateView.as_view(),
        name="admin-usage-create",
    ),
    path(
        "usage/list/",
        AdminUsageListView.as_view(),
        name="admin-usage-list",
    ),
    path(
        "usage/<str:metric>/detail/",
        AdminUsageDetailView.as_view(),
        name="admin-usage-detail",
    ),
    path(
        "usage/adjust/",
        AdminUsageAdjustmentView.as_view(),
        name="admin-usage-adjust",
    ),
]