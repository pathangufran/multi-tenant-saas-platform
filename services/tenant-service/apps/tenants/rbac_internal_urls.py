from django.urls import path
from .rbac_internal_views import (
    InternalRBACPermissionCheckView,
)

urlpatterns = [
    path(
        "rbac/check/",
        InternalRBACPermissionCheckView.as_view(),
        name="internal-rbac-check",
    ),
]