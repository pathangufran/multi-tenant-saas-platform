import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.users.models import EmailVerificationToken

User = get_user_model()

@pytest.mark.django_db
class TestEmailVerification:

    def setup_method(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="verify@example.com",
            password="StrongPassword123",
        )

    def test_user_starts_unverified(self):
        assert self.user.email_verified is False
        assert self.user.email_verified_at is None

    def test_registration_creates_verification_token(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "newuser@example.com",
                "password": "StrongPassword123",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )

        assert response.status_code == 201

        user = User.objects.get(
            email="newuser@example.com",
        )

        token = EmailVerificationToken.objects.get(
            user=user,
        )

        assert token.used_at is None
        assert token.expires_at > timezone.now()

    def test_send_verification_token(self):
        response = self.client.post(
            "/api/v1/auth/email-verification/send/",
            {
                "email": "verify@example.com",
            },
            format="json",
        )

        assert response.status_code == 200

        token = (
            EmailVerificationToken.objects
            .filter(user=self.user)
            .order_by("-created_at")
            .first()
        )

        assert token is not None
        assert token.used_at is None

    def test_verify_email(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        response = self.client.post(
            "/api/v1/auth/email-verification/verify/",
            {
                "token": str(token.token),
            },
            format="json",
        )

        assert response.status_code == 200

        self.user.refresh_from_db()
        token.refresh_from_db()

        assert self.user.email_verified is True
        assert self.user.email_verified_at is not None
        assert token.used_at is not None

    def test_used_token_cannot_be_reused(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            used_at=timezone.now(),
        )

        response = self.client.post(
            "/api/v1/auth/email-verification/verify/",
            {
                "token": str(token.token),
            },
            format="json",
        )

        assert response.status_code == 401

    def test_expired_token_is_rejected(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
        )

        response = self.client.post(
            "/api/v1/auth/email-verification/verify/",
            {
                "token": str(token.token),
            },
            format="json",
        )

        assert response.status_code == 401

    def test_invalid_token_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/email-verification/verify/",
            {
                "token": "00000000-0000-0000-0000-000000000000",
            },
            format="json",
        )

        assert response.status_code == 401

    def test_cannot_verify_already_verified_user(self):
        self.user.email_verified = True
        self.user.email_verified_at = timezone.now()
        self.user.save(
            update_fields=[
                "email_verified",
                "email_verified_at",
            ],
        )

        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        response = self.client.post(
            "/api/v1/auth/email-verification/verify/",
            {
                "token": str(token.token),
            },
            format="json",
        )

        assert response.status_code == 409

    def test_send_for_unknown_user(self):
        response = self.client.post(
            "/api/v1/auth/email-verification/send/",
            {
                "email": "unknown@example.com",
            },
            format="json",
        )

        assert response.status_code == 404

    def test_send_for_already_verified_user(self):
        self.user.email_verified = True
        self.user.email_verified_at = timezone.now()
        self.user.save(
            update_fields=[
                "email_verified",
                "email_verified_at",
            ],
        )

        response = self.client.post(
            "/api/v1/auth/email-verification/send/",
            {
                "email": self.user.email,
            },
            format="json",
        )

        assert response.status_code == 409

    def test_invalid_email_format_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/email-verification/send/",
            {
                "email": "not-an-email",
            },
            format="json",
        )

        assert response.status_code == 400