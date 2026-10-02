from django.urls import path
from .views import (
    ProjectTaskCreateView,
    ProjectTaskListView,
    ProjectTaskDetailsView,
    ProjectTaskUpdateView,
    ProjectTaskDeleteView,
)

urlpatterns = [
    path(
        "",
        ProjectTaskCreateView.as_view(),
        name="task-create",
    ),
    path(
        "list/",
        ProjectTaskListView.as_view(),
        name="task-list",
    ),
    path(
        "<uuid:task_id>/details/",
        ProjectTaskDetailsView.as_view(),
        name="task-details",
    ),
    path(
        "<uuid:task_id>/update/",
        ProjectTaskUpdateView.as_view(),
        name="task-update",
    ),
    path(
        "<uuid:task_id>/delete/",
        ProjectTaskDeleteView.as_view(),
        name="task-delete",
    ),
]