from unittest.mock import patch
from apps.email_service.tasks import (
    send_email_task,
    send_welcome_email,
)

class TestEmailTasks:

    def test_send_email_task_is_registered(self):
        assert (
            send_email_task.name
            == "apps.email_service.tasks.send_mail_task"
        )

    def test_welcome_email_task_is_registered(self):
        assert (
            send_welcome_email.name
            == "apps.email_service.tasks.send_welcome_email"
        )

    @patch(
        "apps.email_service.tasks.EmailService.send_email",
        return_value=1,
    )
    def test_send_email_task(self, mock_send):
        result = send_email_task.apply(
            args=(
                "user@example.com",
                "Subject",
                "Body",
            ),
        )

        assert result.successful()

        assert result.result == {
            "status": "sent",
            "recipient": "user@example.com",
            "sent_count": 1,
        }

        mock_send.assert_called_once_with(
            recipient="user@example.com",
            subject="Subject",
            body="Body",
        )

    @patch(
        "apps.email_service.tasks.EmailService.send_welcome_email",
        return_value=1,
    )
    def test_send_welcome_email_task(self, mock_send):
        result = send_welcome_email.apply(
            args=(
                "user@example.com",
                "Gufran",
            ),
        )

        assert result.successful()

        assert result.result == {
            "status": "sent",
            "recipient": "user@example.com",
            "sent_count": 1,
        }

        mock_send.assert_called_once_with(
            recipient="user@example.com",
            user_name="Gufran",
        )

    @patch(
        "apps.email_service.tasks.EmailService.send_email",
        side_effect=RuntimeError("SMTP unavailable"),
    )
    def test_send_email_task_propagates_failure(
        self,
        mock_send,
    ):
        result = send_email_task.apply(
            args=(
                "user@example.com",
                "Subject",
                "Body",
            ),
        )

        assert result.failed()
        assert isinstance(
            result.result,
            RuntimeError,
        )