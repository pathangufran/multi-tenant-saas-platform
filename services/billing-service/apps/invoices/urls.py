from django.urls import path
from apps.invoices.views import (
    AdminInvoiceDetailView,
    AdminInvoiceCreateView,
    AdminInvoiceListView,
    AdminInvoiceNumberDetailView,
    AdminInvoiceVoidView,
)

urlpatterns = [
    path(
        "admin/create/",
        AdminInvoiceCreateView.as_view(),
        name="admin-invoice-create",
    ),
    path(
        "admin/list/",
        AdminInvoiceListView.as_view(),
        name="admin-invoice-list",
    ),
    path(
        "admin/<uuid:invoice_id>/detail/",
        AdminInvoiceDetailView.as_view(),
        name="admin-invoice-detail",
    ),
    path(
        "admin/<str:invoice_number>/number/detail/",
        AdminInvoiceNumberDetailView.as_view(),
        name="admin-invoice-number-detail",
    ),
    path(
        "admin/<uuid:invoice_id>/void/",
        AdminInvoiceVoidView.as_view(),
        name="admin-invoice-void",
    ),
]