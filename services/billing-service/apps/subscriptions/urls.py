from django.urls import path
from apps.subscriptions.views import (
    AdminSubscriptionCreateView,
    AdminSubscriptionListView,
    AdminSubscriptionDetailView,
    AdminSubscriptionCancelView,
    AdminSubscriptionRenewView,
)

urlpatterns = [
    path(
        "admin/create/",
        AdminSubscriptionCreateView.as_view(),
        name="admin-subscription-create",
    ),
    path(
        "admin/list/",
        AdminSubscriptionListView.as_view(),
        name="admin-subscription-list",
    ),
    path(
        "admin/<uuid:subscription_id>/detail/",
        AdminSubscriptionDetailView.as_view(),
        name="admin-subscription-detail",
    ),
    path(
        "admin/<uuid:subscription_id>/cancel/",
        AdminSubscriptionCancelView.as_view(),
        name="admin-subscription-cancel",
    ),
    path(
        "admin/<uuid:subscription_id>/renew/",
        AdminSubscriptionRenewView.as_view(),
        name="admin-subscription-renew",
    ),
]