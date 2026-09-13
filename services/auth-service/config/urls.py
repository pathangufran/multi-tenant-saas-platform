"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import logging
from django.contrib import admin
from django.urls import path,include
from django.http import JsonResponse
from apps.common.exceptions import (
    ResourceNotFoundError,
)
from apps.common.health_views import (
    health_check,
    readiness_check,
)

logger = logging.getLogger(__name__)

def test_error(request):
    raise ResourceNotFoundError(
        message="Test resource does not exist.",
        code="TEST_RESOURCE_NOT_FOUND",
    )

def test_logging(request):
    logger.info("Testing structured logging")

    return JsonResponse(
        {
            "message": "Logging test successful",
            "request_id": request.request_id,
        }
    )

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.users.urls')),

    path('test-error/', test_error),
    path('test-logging/', test_logging),
    path("health/", health_check),
    path("ready/", readiness_check),
]
