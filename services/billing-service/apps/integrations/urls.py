from django.urls import path
from .views import (
    AdminBillingEventDetailView,
    AdminBillingEventListView,
    AdminBillingEventRetryView,
)

urlpatterns = [
    path(
        "billing-events/list/",
        AdminBillingEventListView.as_view(),
        name="admin-billing-event-list",
    ),
    path(
        "billing-events/<uuid:event_id>/detail/",
        AdminBillingEventDetailView.as_view(),
        name="admin-billing-event-detail",
    ),
    path(
        "billing-events/<uuid:event_id>/retry/",
        AdminBillingEventRetryView.as_view(),
        name="admin-billing-event-retry",
    ),
]