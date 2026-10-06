import pytest
from unittest.mock import patch
from apps.email_service.services import EmailService

class TestEmailService:

    @patch(
        "apps.email_service.services.EmailProvider.send",
        return_value=1,
    )
    def test_send_email(self, mock_send):
        result = EmailService.send_email(
            recipient="user@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result == 1
        mock_send.assert_called_once()

        message = mock_send.call_args.args[0]

        assert message.recipient == "user@example.com"
        assert message.subject == "Test Subject"
        assert message.body == "Test body"

    def test_send_email_requires_recipient(self):
        with pytest.raises(ValueError):
            EmailService.send_email(
                recipient="",
                subject="Subject",
                body="Body",
            )

    def test_send_email_requires_subject(self):
        with pytest.raises(ValueError):
            EmailService.send_email(
                recipient="user@example.com",
                subject="",
                body="Body",
            )

    def test_send_email_requires_body(self):
        with pytest.raises(ValueError):
            EmailService.send_email(
                recipient="user@example.com",
                subject="Subject",
                body="",
            )

    @patch(
        "apps.email_service.services.EmailProvider.send",
        return_value=1,
    )
    def test_send_welcome_email(self, mock_send):
        result = EmailService.send_welcome_email(
            recipient="user@example.com",
            user_name="Gufran",
        )

        assert result == 1
        mock_send.assert_called_once()

        message = mock_send.call_args.args[0]

        assert message.recipient == "user@example.com"
        assert message.subject == (
            "Welcome to the SaaS Platform"
        )
        assert "Gufran" in message.body

    def test_welcome_email_requires_user_name(self):
        with pytest.raises(ValueError):
            EmailService.send_welcome_email(
                recipient="user@example.com",
                user_name="",
            )