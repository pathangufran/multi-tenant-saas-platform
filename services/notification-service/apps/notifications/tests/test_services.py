import uuid
import pytest
from apps.notifications.models import (
    Notification,
    NotificationPreference,
)
from apps.notifications.services import NotificationService

@pytest.mark.django_db
class TestNotificationService:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_default_preference_enables_in_app_notification(self):
        enabled = NotificationService.is_in_app_enabled(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
        )

        assert enabled is True

        preference = NotificationPreference.objects.get(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
        )

        assert preference.in_app_enabled is True

    def test_create_notification(self):
        notification = (
            NotificationService.create_notification(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                event_type=Notification.EventType.TASK_ASSIGNED,
                title="Task Assigned",
                message="You have been assigned a task.",
            )
        )

        assert notification is not None
        assert notification.tenant_id == self.tenant_id
        assert notification.user_id == self.user_id
        assert (
            notification.event_type
            == Notification.EventType.TASK_ASSIGNED
        )
        assert notification.status == Notification.Status.UNREAD

    def test_create_notification_with_metadata(self):
        resource_id = uuid.uuid4()

        notification = (
            NotificationService.create_notification(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                event_type=Notification.EventType.REPORT_READY,
                title="Report Ready",
                message="Your report is ready.",
                resource_type="report",
                resource_id=resource_id,
                metadata={
                    "format": "csv",
                },
            )
        )

        assert notification.resource_type == "report"
        assert notification.resource_id == resource_id
        assert notification.metadata == {
            "format": "csv",
        }

    def test_notification_skipped_when_in_app_disabled(self):
        NotificationPreference.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_COMPLETED,
            in_app_enabled=False,
        )

        notification = (
            NotificationService.create_notification(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                event_type=Notification.EventType.TASK_COMPLETED,
                title="Task Completed",
                message="Your task has been completed.",
            )
        )

        assert notification is None
        assert not Notification.objects.filter(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        ).exists()

    def test_list_notifications_is_user_and_tenant_scoped(self):
        other_tenant = uuid.uuid4()
        other_user = uuid.uuid4()

        Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Valid",
            message="Valid notification",
        )

        Notification.objects.create(
            tenant_id=other_tenant,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Other Tenant",
            message="Other tenant notification",
        )

        Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=other_user,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Other User",
            message="Other user notification",
        )

        notifications = NotificationService.list_notifications(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

        assert notifications.count() == 1
        assert notifications.first().title == "Valid"

    def test_mark_as_read(self):
        notification = Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Task Assigned",
            message="You have a new task.",
        )

        result = NotificationService.mark_as_read(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            notification_id=notification.id,
        )

        assert result is not None
        assert result.status == Notification.Status.READ
        assert result.read_at is not None

    def test_mark_as_unread(self):
        notification = Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Task Assigned",
            message="You have a new task.",
            status=Notification.Status.READ,
        )

        result = NotificationService.mark_as_unread(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            notification_id=notification.id,
        )

        assert result is not None
        assert result.status == Notification.Status.UNREAD
        assert result.read_at is None

    def test_cross_tenant_notification_cannot_be_marked_read(
        self,
    ):
        notification = Notification.objects.create(
            tenant_id=uuid.uuid4(),
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Task Assigned",
            message="You have a new task.",
        )

        result = NotificationService.mark_as_read(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            notification_id=notification.id,
        )

        assert result is None

        notification.refresh_from_db()

        assert notification.status == Notification.Status.UNREAD

    def test_cross_user_notification_cannot_be_marked_read(self):
        notification = Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=uuid.uuid4(),
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Task Assigned",
            message="You have a new task.",
        )

        result = NotificationService.mark_as_read(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            notification_id=notification.id,
        )

        assert result is None

    def test_unread_count(self):
        Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_ASSIGNED,
            title="Unread 1",
            message="Unread",
        )

        Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.TASK_COMPLETED,
            title="Unread 2",
            message="Unread",
        )

        Notification.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            event_type=Notification.EventType.REPORT_READY,
            title="Read",
            message="Read",
            status=Notification.Status.READ,
        )

        count = NotificationService.unread_count(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
        )

        assert count == 2

    def test_create_notification_requires_tenant(self):
        with pytest.raises(ValueError):
            NotificationService.create_notification(
                tenant_id=None,
                user_id=self.user_id,
                event_type=Notification.EventType.TASK_ASSIGNED,
                title="Task",
                message="Message",
            )

    def test_create_notification_requires_user(self):
        with pytest.raises(ValueError):
            NotificationService.create_notification(
                tenant_id=self.tenant_id,
                user_id=None,
                event_type=Notification.EventType.TASK_ASSIGNED,
                title="Task",
                message="Message",
            )

    def test_create_notification_requires_title(self):
        with pytest.raises(ValueError):
            NotificationService.create_notification(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                event_type=Notification.EventType.TASK_ASSIGNED,
                title="   ",
                message="Message",
            )

    def test_create_notification_requires_message(self):
        with pytest.raises(ValueError):
            NotificationService.create_notification(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                event_type=Notification.EventType.TASK_ASSIGNED,
                title="Task",
                message="   ",
            )