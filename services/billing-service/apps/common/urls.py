from django.urls import path
from apps.common.views import (
    HealthView, ReadinessView,
)
from apps.common.monitoring_views import (
    AdminCeleryMonitoringView,
)

urlpatterns = [
    path(
        "health/",
        HealthView.as_view(),
        name="health"
    ),
    path(
        "ready/",
        ReadinessView.as_view(),
        name="readiness"
    ),
    path(
        "admin/monitoring/celery/",
        AdminCeleryMonitoringView.as_view(),
        name="admin-celery-monitoring",
    ),
]
