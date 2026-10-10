from django.urls import path
from apps.plans.views import (
    AdminPlanCreateView,
    AdminPlanListView,
    AdminPlanDetailView,
    AdminPlanUpdateView,
    AdminPlanDeleteView,
    PublicPlanListView,
    PublicPlanDetailView,
)

urlpatterns = [
    path(
        "list/", 
        PublicPlanListView.as_view(), 
        name="public-plan-list"
    ),
    path(
        "<str:code>/detail/", 
        PublicPlanDetailView.as_view(), 
        name="public-plan-detail"
    ),
    path(
        "admin/create/",
        AdminPlanCreateView.as_view(),
        name="admin-plan-create",
    ),
    path(
        "admin/list/",
        AdminPlanListView.as_view(),
        name="admin-plan-list",
    ),
    path(
        "admin/<uuid:plan_id>/detail/",
        AdminPlanDetailView.as_view(),
        name="admin-plan-detail",
    ),
    path(
        "admin/<uuid:plan_id>/update/",
        AdminPlanUpdateView.as_view(),
        name="admin-plan-update",
    ),
    path(
        "admin/<uuid:plan_id>/delete/",
        AdminPlanDeleteView.as_view(),
        name="admin-plan-delete",
    ),
]