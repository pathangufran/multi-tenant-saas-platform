from django.urls import path
from .views import TenantCreateView

urlpatterns = [
    path("", TenantCreateView.as_view(), name="tenant-create"),
]