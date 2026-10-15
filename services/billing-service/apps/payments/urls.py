from django.urls import path
from apps.payments.views import (
    AdminPaymentCreateView,
    AdminPaymentListView,
    AdminPaymentDetailView,
    PaymentWebhookView,
)

urlpatterns = [
    path(
        "admin/create/",
        AdminPaymentCreateView.as_view(),
        name="admin-payment-create",
    ),
    path(
        "admin/list/",
        AdminPaymentListView.as_view(),
        name="admin-payment-list",
    ),
    path(
        "admin/<uuid:payment_id>/detail/",
        AdminPaymentDetailView.as_view(),
        name="admin-payment-detail",
    ),
    path(
        "webhooks/payment/",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
]