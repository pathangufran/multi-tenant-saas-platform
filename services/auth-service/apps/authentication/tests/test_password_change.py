import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@pytest.mark.django_db
class TestPasswordChange:

    def setup_method(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="password@example.com",
            password="OldPassword123",
        )

        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}",
        )

    def test_authenticated_user_can_change_password(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
                "new_password": "NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 200

        assert response.data == {
            "message": "Password changed successfully.",
        }

        self.user.refresh_from_db()

        assert self.user.check_password(
            "NewPassword123"
        )

        assert not self.user.check_password(
            "OldPassword123"
        )

    def test_wrong_current_password_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "WrongPassword123",
                "new_password": "NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 401

        assert response.data["error"]["code"] == (
            "AUTHENTICATION_ERROR"
        )

        self.user.refresh_from_db()

        assert self.user.check_password(
            "OldPassword123"
        )

    def test_new_password_must_be_different(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
                "new_password": "OldPassword123",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_new_password_cannot_have_leading_whitespace(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
                "new_password": " NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_new_password_cannot_have_trailing_whitespace(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
                "new_password": "NewPassword123 ",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_new_password_must_have_minimum_length(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
                "new_password": "Short1",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_unauthenticated_user_cannot_change_password(self):
        self.client.credentials()

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
                "new_password": "NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 401

    def test_missing_current_password_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "new_password": "NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_missing_new_password_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "OldPassword123",
            },
            format="json",
        )

        assert response.status_code == 400