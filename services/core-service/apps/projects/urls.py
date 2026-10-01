from django.urls import path
from .views import (
    ProjectCreateView,
    ProjectListView,
    ProjectDetailView,
    ProjectUpdateView,
    ProjectDeleteView,
)

urlpatterns = [
    path(
        "",
        ProjectCreateView.as_view(),
        name="project-create",
    ),
    path(
        "list/",
        ProjectListView.as_view(),
        name="project-list",
    ),
    path(
        "<uuid:project_id>/details/",
        ProjectDetailView.as_view(),
        name="project-details",
    ),
    path(
        "<uuid:project_id>/update/",
        ProjectUpdateView.as_view(),
        name="project-update",
    ),
    path(
        "<uuid:project_id>/delete/",
        ProjectDeleteView.as_view(),
        name="project-delete",
    ),
]