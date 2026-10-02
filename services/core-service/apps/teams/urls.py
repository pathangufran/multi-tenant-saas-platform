from django.urls import path
from .views import (
    TeamCreateView,
    TeamListView,
    TeamDetailView,
    TeamUpdateView,
    TeamDeleteView,
)

urlpatterns = [
    path(
        "",
        TeamCreateView.as_view(),
        name="team-create",
    ),
    path(
        "list/",
        TeamListView.as_view(),
        name="team-list",
    ),
    path(
        "<uuid:team_id>/details/",
        TeamDetailView.as_view(),
        name="team-details",
    ),
    path(
        "<uuid:team_id>/update/",
        TeamUpdateView.as_view(),
        name="team-update",
    ),
    path(
        "<uuid:team_id>/delete/",
        TeamDeleteView.as_view(),
        name="team-delete",
    ),
]