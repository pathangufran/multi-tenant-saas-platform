import uuid
import pytest
from unittest.mock import MagicMock, patch
from apps.common.async_integration import (
    AsyncEvent,
    AsyncEventDispatcher,
    AsyncIntegrationError,
    AsyncJobDispatcher,
    UnsupportedEventError,
)
from apps.common.async_service import (
    AsyncIntegrationService,
)
from apps.common.event_publishers import (
    EventPublisher,
)

class TestAsyncEventDispatcher:

    def test_get_task_name_for_supported_event(self):

        task_name = (
            AsyncEventDispatcher.get_task_name(
                event_type="TASK_ASSIGNED",
            )
        )

        assert (
            task_name
            == "apps.notifications.tasks.process_notification"
        )

    def test_get_task_name_rejects_unknown_event(self):

        with pytest.raises(
            UnsupportedEventError,
            match="No async handler registered",
        ):

            AsyncEventDispatcher.get_task_name(
                event_type="UNKNOWN_EVENT",
            )

    @patch(
        "apps.common.async_integration.current_app"
    )
    def test_dispatch_sends_event_to_celery(
        self,
        celery_app,
    ):

        celery_result = MagicMock()
        celery_result.id = "celery-123"

        celery_app.send_task.return_value = (
            celery_result
        )

        event = AsyncEvent(
            event_id="event-123",
            event_type="TASK_ASSIGNED",
            tenant_id="tenant-123",
            user_id="user-123",
            payload={
                "task_id": "task-123",
            },
        )

        result = (
            AsyncEventDispatcher.dispatch(
                event=event,
            )
        )

        assert result == celery_result

        celery_app.send_task.assert_called_once_with(
            "apps.notifications.tasks.process_notification",
            kwargs={
                "event_id": "event-123",
                "event_type": "TASK_ASSIGNED",
                "tenant_id": "tenant-123",
                "user_id": "user-123",
                "payload": {
                    "task_id": "task-123",
                },
            },
        )


class TestAsyncJobDispatcher:

    @patch(
        "apps.common.async_integration.current_app"
    )
    def test_dispatch_task_with_arguments(
        self,
        celery_app,
    ):

        celery_result = MagicMock()

        celery_app.send_task.return_value = (
            celery_result
        )

        result = (
            AsyncJobDispatcher.dispatch_task(
                task_name="apps.reports.tasks.generate_report",
                args=[
                    "tenant-123",
                ],
                kwargs={
                    "report_type": "TASK_SUMMARY",
                },
            )
        )

        assert result == celery_result

        celery_app.send_task.assert_called_once_with(
            "apps.reports.tasks.generate_report",
            args=[
                "tenant-123",
            ],
            kwargs={
                "report_type": "TASK_SUMMARY",
            },
        )

    @patch(
        "apps.common.async_integration.current_app"
    )
    def test_dispatch_task_supports_countdown(
        self,
        celery_app,
    ):

        AsyncJobDispatcher.dispatch_task(
            task_name="apps.exports.tasks.generate_export",
            args=[
                "export-123",
            ],
            countdown=30,
        )

        celery_app.send_task.assert_called_once_with(
            "apps.exports.tasks.generate_export",
            args=[
                "export-123",
            ],
            kwargs={},
            countdown=30,
        )

class TestAsyncIntegrationService:

    def test_create_event_generates_event_id(self):

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        event = (
            AsyncIntegrationService.create_event(
                event_type="TASK_COMPLETED",
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "task_id": "task-123",
                },
            )
        )

        assert event.event_id is not None

        assert (
            event.event_type
            == "TASK_COMPLETED"
        )

        assert (
            event.tenant_id
            == str(tenant_id)
        )

        assert (
            event.user_id
            == str(user_id)
        )

        assert event.payload == {
            "task_id": "task-123",
        }

    def test_create_event_supports_platform_event(self):

        event = (
            AsyncIntegrationService.create_event(
                event_type="PASSWORD_RESET",
                tenant_id=None,
                user_id=None,
            )
        )

        assert event.tenant_id is None

        assert event.user_id is None

        assert event.payload == {}

    @patch(
        "apps.common.async_service.dispatch_event"
    )
    def test_dispatch_event_enqueues_event(
        self,
        dispatch_task,
    ):

        dispatch_task.delay.return_value = (
            MagicMock(id="celery-123")
        )

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        result = (
            AsyncIntegrationService.dispatch_event(
                event_type="TASK_ASSIGNED",
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "task_id": "task-123",
                },
            )
        )

        assert result.id == "celery-123"

        dispatch_task.delay.assert_called_once()

        args = (
            dispatch_task.delay.call_args.args
        )

        assert len(args) == 5

        assert (
            args[1]
            == "TASK_ASSIGNED"
        )

        assert (
            args[2]
            == str(tenant_id)
        )

        assert (
            args[3]
            == str(user_id)
        )

        assert args[4] == {
            "task_id": "task-123",
        }

    @patch(
        "apps.common.async_service.AsyncJobDispatcher.dispatch_task"
    )
    def test_generate_report_dispatches_report_task(
        self,
        dispatch_task,
    ):

        dispatch_task.return_value = (
            MagicMock(id="report-task-123")
        )

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        result = (
            AsyncIntegrationService.generate_report(
                tenant_id=tenant_id,
                report_type="TASK_SUMMARY",
                requested_by=user_id,
            )
        )

        assert result.id == "report-task-123"

        dispatch_task.assert_called_once_with(
            task_name=(
                "apps.reports.tasks.generate_report"
            ),
            kwargs={
                "tenant_id": str(tenant_id),
                "report_type": "TASK_SUMMARY",
                "requested_by": str(user_id),
            },
        )

    @patch(
        "apps.common.async_service.AsyncJobDispatcher.dispatch_task"
    )
    def test_generate_export_dispatches_export_task(
        self,
        dispatch_task,
    ):

        dispatch_task.return_value = (
            MagicMock(id="export-task-123")
        )

        export_id = uuid.uuid4()

        result = (
            AsyncIntegrationService.generate_export(
                export_id=export_id,
            )
        )

        assert result.id == "export-task-123"

        dispatch_task.assert_called_once_with(
            task_name=(
                "apps.exports.tasks.generate_export"
            ),
            args=[
                str(export_id),
            ],
        )

class TestEventPublisher:

    @patch(
        "apps.common.event_publishers.AsyncIntegrationService.dispatch_event"
    )
    def test_task_assigned_publishes_event(
        self,
        dispatch_event,
    ):

        dispatch_event.return_value = (
            MagicMock(id="celery-123")
        )

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        assigned_by = uuid.uuid4()

        result = EventPublisher.task_assigned(
            tenant_id=tenant_id,
            user_id=user_id,
            task_id=task_id,
            assigned_by=assigned_by,
        )

        assert result.id == "celery-123"

        dispatch_event.assert_called_once_with(
            event_type="TASK_ASSIGNED",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "task_id": str(task_id),
                "assigned_by": str(assigned_by),
            },
        )

    @patch(
        "apps.common.event_publishers.AsyncIntegrationService.dispatch_event"
    )
    def test_task_completed_publishes_event(
        self,
        dispatch_event,
    ):

        EventPublisher.task_completed(
            tenant_id="tenant-123",
            user_id="user-123",
            task_id="task-123",
            completed_by="user-456",
        )

        dispatch_event.assert_called_once_with(
            event_type="TASK_COMPLETED",
            tenant_id="tenant-123",
            user_id="user-123",
            payload={
                "task_id": "task-123",
                "completed_by": "user-456",
            },
        )

    @patch(
        "apps.common.event_publishers.AsyncIntegrationService.dispatch_event"
    )
    def test_payment_failed_publishes_event(
        self,
        dispatch_event,
    ):

        EventPublisher.payment_failed(
            tenant_id="tenant-123",
            user_id="user-123",
            payment_id="payment-123",
        )

        dispatch_event.assert_called_once_with(
            event_type="PAYMENT_FAILED",
            tenant_id="tenant-123",
            user_id="user-123",
            payload={
                "payment_id": "payment-123",
            },
        )

    @patch(
        "apps.common.event_publishers.AsyncIntegrationService.dispatch_event"
    )
    def test_report_ready_publishes_event(
        self,
        dispatch_event,
    ):

        EventPublisher.report_ready(
            tenant_id="tenant-123",
            user_id="user-123",
            report_id="report-123",
        )

        dispatch_event.assert_called_once_with(
            event_type="REPORT_READY",
            tenant_id="tenant-123",
            user_id="user-123",
            payload={
                "report_id": "report-123",
            },
        )