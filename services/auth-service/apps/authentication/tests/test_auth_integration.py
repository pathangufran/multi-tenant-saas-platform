import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationIntegration:

    def setup_method(self):
        self.client = APIClient()

    def test_complete_authentication_flow(self):
        # Register
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "integration@example.com",
                "password": "StrongPassword123",
                "first_name": "Integration",
                "last_name": "User",
            },
            format="json",
        )

        assert response.status_code == 201

        # Login
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "integration@example.com",
                "password": "StrongPassword123",
            },
            format="json",
        )

        assert response.status_code == 200

        access_token = response.data["access_token"]
        refresh_token = response.data["refresh_token"]

        # Current user
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        response = self.client.get(
            "/api/v1/auth/me/",
        )

        assert response.status_code == 200
        assert response.data["email"] == (
            "integration@example.com"
        )

        # Password change
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "StrongPassword123",
                "new_password": "NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 200

        # Logout
        self.client.credentials()

        response = self.client.post(
            "/api/v1/auth/logout/",
            {
                "refresh_token": refresh_token,
            },
            format="json",
        )

        assert response.status_code == 200

        # Old refresh token must no longer work
        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {
                "refresh_token": refresh_token,
            },
            format="json",
        )

        assert response.status_code == 401