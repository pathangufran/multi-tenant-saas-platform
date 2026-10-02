from django.urls import path
from .views import (
    TaskAttachmentCreateView,
    TaskAttachmentListView,
    TaskAttachmentDetailView,
    TaskAttachmentDeleteView,
)

urlpatterns = [
    path(
        "",
        TaskAttachmentCreateView.as_view(),
        name="attachment-create",
    ),
    path(
        "list/",
        TaskAttachmentListView.as_view(),
        name="attachment-list",
    ),
    path(
        "<uuid:attachment_id>/details/",
        TaskAttachmentDetailView.as_view(),
        name="attachment-details",
    ),
    path(
        "<uuid:attachment_id>/delete/",
        TaskAttachmentDeleteView.as_view(),
        name="attachment-delete",
    ),
]