import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@pytest.mark.django_db
class TestLogout:

    def setup_method(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="logout@example.com",
            password="StrongPassword123",
        )

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)

        response = self.client.post(
            "/api/v1/auth/logout/",
            {
                "refresh_token": str(refresh),
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data == {
            "message": "Successfully logged out.",
        }

        refresh_response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {
                "refresh_token": str(refresh),
            },
            format="json",
        )

        assert refresh_response.status_code == 401

    def test_logout_with_invalid_refresh_token(self):
        response = self.client.post(
            "/api/v1/auth/logout/",
            {
                "refresh_token": "invalid-token",
            },
            format="json",
        )

        assert response.status_code == 401

        assert response.data["error"]["code"] == (
            "AUTHENTICATION_ERROR"
        )

    def test_logout_requires_refresh_token(self):
        response = self.client.post(
            "/api/v1/auth/logout/",
            {},
            format="json",
        )

        assert response.status_code == 400

    def test_logout_with_empty_refresh_token(self):
        response = self.client.post(
            "/api/v1/auth/logout/",
            {
                "refresh_token": "",
            },
            format="json",
        )

        assert response.status_code == 400