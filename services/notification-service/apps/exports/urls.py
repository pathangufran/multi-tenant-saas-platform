from django.urls import path
from .views import (
    ExportCreateView,
    ExportDetailView,
    ExportDownloadView,
    ExportListView,
)

urlpatterns = [
    path(
        "",
        ExportCreateView.as_view(),
        name="export-create",
    ),
    path(
        "list/",
        ExportListView.as_view(),
        name="export-list",
    ),
    path(
        "<uuid:export_id>/",
        ExportDetailView.as_view(),
        name="export-detail",
    ),
    path(
        "<uuid:export_id>/download/",
        ExportDownloadView.as_view(),
        name="export-download",
    ),
]