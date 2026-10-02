from django.urls import path
from .views import (
    TaskCommentCreateView,
    TaskCommentListView,
    TaskCommentDetailView,
    TaskCommentUpdateView,
    TaskCommentDeleteView,
)

urlpatterns = [
    path(
        "",
        TaskCommentCreateView.as_view(),
        name="comment-create",
    ),
    path(
        "list/",
        TaskCommentListView.as_view(),
        name="comment-list",
    ),
    path(
        "<uuid:comment_id>/details/",
        TaskCommentDetailView.as_view(),
        name="comment-details",
    ),
    path(
        "<uuid:comment_id>/update/",
        TaskCommentUpdateView.as_view(),
        name="comment-update",
    ),
    path(
        "<uuid:comment_id>/delete/",
        TaskCommentDeleteView.as_view(),
        name="comment-delete",
    ),
]