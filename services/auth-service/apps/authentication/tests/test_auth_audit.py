import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.authentication.models import AuthenticationAuditEvent

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationAudit:

    def setup_method(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="audit@example.com",
            password="StrongPassword123",
        )

    def test_successful_login_creates_audit_event(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "audit@example.com",
                "password": "StrongPassword123",
            },
            format="json",
            HTTP_X_REQUEST_ID="test-login-request",
        )

        assert response.status_code == 200

        event = (
            AuthenticationAuditEvent.objects
            .filter(
                event_type=(
                    AuthenticationAuditEvent
                    .EventType
                    .LOGIN_SUCCESS
                )
            )
            .first()
        )

        assert event is not None
        assert event.user == self.user
        assert event.request_id == "test-login-request"

    def test_failed_login_creates_audit_event(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "audit@example.com",
                "password": "WrongPassword123",
            },
            format="json",
        )

        assert response.status_code == 401

        event = (
            AuthenticationAuditEvent.objects
            .filter(
                event_type=(
                    AuthenticationAuditEvent
                    .EventType
                    .LOGIN_FAILURE
                )
            )
            .first()
        )

        assert event is not None
        assert event.user == self.user
        assert event.metadata["reason"] == "invalid_credentials"

    def test_unknown_user_login_is_audited(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "unknown@example.com",
                "password": "WrongPassword123",
            },
            format="json",
        )

        assert response.status_code == 401

        event = (
            AuthenticationAuditEvent.objects
            .filter(
                event_type=(
                    AuthenticationAuditEvent
                    .EventType
                    .LOGIN_FAILURE
                )
            )
            .first()
        )

        assert event is not None
        assert event.user is None

    def test_password_change_creates_audit_event(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": self.user.email,
                "password": "StrongPassword123",
            },
            format="json",
        )

        access_token = response.data["access_token"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "StrongPassword123",
                "new_password": "NewPassword123",
            },
            format="json",
        )

        assert response.status_code == 200

        assert AuthenticationAuditEvent.objects.filter(
            user=self.user,
            event_type=(
                AuthenticationAuditEvent
                .EventType
                .PASSWORD_CHANGED
            ),
        ).exists()
        
    def test_audit_event_does_not_store_password_or_token(self):
        event = AuthenticationAuditEvent.objects.create(
            user=self.user,
            event_type=(
                AuthenticationAuditEvent
                .EventType
                .LOGIN_SUCCESS
            ),
            metadata={
                "provider": "password",
            },
        )

        assert "password" not in event.metadata
        assert "access_token" not in event.metadata
        assert "refresh_token" not in event.metadata