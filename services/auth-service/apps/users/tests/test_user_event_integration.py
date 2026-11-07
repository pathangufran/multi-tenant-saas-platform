import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from apps.outbox.models import OutboxEvent
from apps.users.models import EmailVerificationToken
from apps.users.services import UserService
from apps.authentication.email_verification_service import (
    EmailVerificationService,
)

User = get_user_model()

class UserRegistrationEventTests(TestCase):

    def test_registration_creates_user_registered_event(self):
        user = UserService.register_user(
            email="registered@example.com",
            password="StrongPassword123!",
            first_name="Test",
            last_name="User",
        )

        event = OutboxEvent.objects.get(
            event_type="user.registered",
            aggregate_id=str(user.id),
        )

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )

        self.assertEqual(
            event.data["user_id"],
            str(user.id),
        )

        self.assertEqual(
            event.data["email"],
            user.email,
        )

        self.assertTrue(
            EmailVerificationToken.objects.filter(
                user=user,
            ).exists()
        )

    def test_registration_rolls_back_when_outbox_creation_fails(self):
        from unittest.mock import patch

        with patch(
            "apps.users.services.OutboxService.record_event",
            side_effect=RuntimeError("Outbox failure"),
        ):
            with self.assertRaises(RuntimeError):
                UserService.register_user(
                    email="rollback@example.com",
                    password="StrongPassword123!",
                )

        self.assertFalse(
            User.objects.filter(
                email="rollback@example.com",
            ).exists()
        )

        self.assertFalse(
            EmailVerificationToken.objects.filter(
                user__email="rollback@example.com",
            ).exists()
        )

class EmailVerificationEventTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="verify-event@example.com",
            password="StrongPassword123!",
        )

        self.token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
        )

    def test_email_verification_creates_event(self):
        verified_user = EmailVerificationService.verify_email(
            token=str(self.token.token),
        )

        event = OutboxEvent.objects.get(
            event_type="user.email_verified",
            aggregate_id=str(self.user.id),
        )

        verified_user.refresh_from_db()

        self.assertTrue(verified_user.email_verified)

        self.assertEqual(
            event.data["user_id"],
            str(self.user.id),
        )

        self.assertEqual(
            event.data["email"],
            self.user.email,
        )

        self.assertEqual(event.aggregate_version, 2)

    def test_email_verification_rolls_back_when_outbox_fails(self):
        from unittest.mock import patch

        with patch(
            "apps.authentication.email_verification_service."
            "OutboxService.record_event",
            side_effect=RuntimeError("Outbox failure"),
        ):
            with self.assertRaises(RuntimeError):
                EmailVerificationService.verify_email(
                    token=str(self.token.token),
                )

        self.user.refresh_from_db()
        self.token.refresh_from_db()

        self.assertFalse(self.user.email_verified)
        self.assertIsNone(self.user.email_verified_at)
        self.assertIsNone(self.token.used_at)

        self.assertFalse(
            OutboxEvent.objects.filter(
                event_type="user.email_verified",
                aggregate_id=str(self.user.id),
            ).exists()
        )