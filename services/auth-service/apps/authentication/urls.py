from django.urls import path
from .views import (
    LoginView,TokenRefreshView,LogoutView,
)

urlpatterns = [
    path("login/",LoginView.as_view(),name="login",),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
]