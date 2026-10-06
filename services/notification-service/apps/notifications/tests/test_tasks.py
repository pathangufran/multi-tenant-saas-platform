import uuid
import pytest
from unittest.mock import patch
from apps.notifications.models import Notification
from apps.notifications.tasks import (
    mark_notification_read,
    process_notification,
)

@pytest.mark.django_db
class TestNotificationTasks:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_process_notification_is_registered(self):
        assert (
            process_notification.name
            == "apps.notifications.tasks.process_notification"
        )

    def test_process_notification_creates_notification(self):
        result = process_notification.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "user_id": str(self.user_id),
                "event_type": Notification.EventType.TASK_ASSIGNED,
                "title": "Task Assigned",
                "message": "You have been assigned a task.",
            },
        )

        assert result.successful()

        assert result.result["status"] == "created"

        assert Notification.objects.filter(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        ).count() == 1

    def test_process_notification_respects_preference(self):
        from apps.notifications.models import (
            NotificationPreference,
        )

        NotificationPreference.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_COMPLETED,
            in_app_enabled=False,
        )

        result = process_notification.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "user_id": str(self.user_id),
                "event_type": Notification.EventType.TASK_COMPLETED,
                "title": "Task Completed",
                "message": "The task has been completed.",
            },
        )

        assert result.successful()

        assert result.result == {
            "status": "skipped",
            "reason": "in_app_notifications_disabled",
        }

        assert not Notification.objects.filter(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        ).exists()

    @patch(
        "apps.notifications.tasks.NotificationService.create_notification",
        side_effect=RuntimeError("database unavailable"),
    )
    def test_process_notification_propagates_failure(
        self,
        mock_create,
    ):
        result = process_notification.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "user_id": str(self.user_id),
                "event_type": Notification.EventType.TASK_ASSIGNED,
                "title": "Task Assigned",
                "message": "You have been assigned a task.",
            },
        )

        assert result.failed()
        assert isinstance(
            result.result,
            RuntimeError,
        )

        mock_create.assert_called_once()

    def test_mark_notification_read_task(self):
        notification = Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Task Assigned",
            message="You have a task.",
        )

        result = mark_notification_read.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "user_id": str(self.user_id),
                "notification_id": str(notification.id),
            },
        )

        assert result.successful()

        assert result.result == {
            "status": "read",
            "notification_id": str(notification.id),
        }

        notification.refresh_from_db()

        assert notification.status == Notification.Status.READ

    def test_mark_notification_read_not_found(self):
        result = mark_notification_read.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "user_id": str(self.user_id),
                "notification_id": str(uuid.uuid4()),
            },
        )

        assert result.successful()

        assert result.result == {
            "status": "not_found",
        }