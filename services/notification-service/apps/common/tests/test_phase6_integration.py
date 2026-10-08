import pytest
from unittest.mock import MagicMock, patch
from apps.common.async_integration import (
    AsyncEvent,
    AsyncEventDispatcher,
    UnsupportedEventError,
)
from apps.common.async_service import (
    AsyncIntegrationService,
)
from apps.common.event_publishers import (
    EventPublisher,
)
from apps.common.retry import (
    AuthenticationTaskError,
    PermanentTaskError,
    RetryPolicy,
    TransientTaskError,
    ValidationTaskError,
)

class TestPhase6EventFlow:

    @patch(
        "apps.common.async_service.dispatch_event"
    )
    def test_task_assigned_event_flow(
        self,
        dispatch_event,
    ):
        celery_result = MagicMock(
            id="celery-task-123"
        )

        dispatch_event.delay.return_value = (
            celery_result
        )

        result = EventPublisher.task_assigned(
            tenant_id="tenant-123",
            user_id="user-123",
            task_id="task-123",
            assigned_by="user-456",
        )

        assert result.id == "celery-task-123"

        dispatch_event.delay.assert_called_once()

        args = dispatch_event.delay.call_args.args

        assert len(args) == 5

        assert args[1] == "TASK_ASSIGNED"
        assert args[2] == "tenant-123"
        assert args[3] == "user-123"

        assert args[4] == {
            "task_id": "task-123",
            "assigned_by": "user-456",
        }

class TestPhase6EventRouting:

    def test_all_supported_notification_events_have_handlers(self):

        supported_events = [
            "USER_INVITED",
            "TASK_ASSIGNED",
            "TASK_COMPLETED",
            "PASSWORD_RESET",
            "SUBSCRIPTION_CREATED",
            "PAYMENT_FAILED",
            "REPORT_READY",
        ]

        for event_type in supported_events:

            task_name = (
                AsyncEventDispatcher.get_task_name(
                    event_type=event_type
                )
            )

            assert task_name == (
                "apps.notifications.tasks.process_notification"
            )

    def test_unknown_event_fails_closed(self):

        with pytest.raises(
            UnsupportedEventError
        ):
            AsyncEventDispatcher.get_task_name(
                event_type="INVALID_EVENT"
            )

class TestPhase6ReportFlow:

    @patch(
        "apps.common.async_service.AsyncJobDispatcher.dispatch_task"
    )
    def test_report_generation_is_async(
        self,
        dispatch_task,
    ):
        celery_result = MagicMock(
            id="report-job-123"
        )

        dispatch_task.return_value = (
            celery_result
        )

        result = (
            AsyncIntegrationService.generate_report(
                tenant_id="tenant-123",
                report_type="TASK_SUMMARY",
                requested_by="user-123",
            )
        )

        assert result.id == "report-job-123"

        dispatch_task.assert_called_once_with(
            task_name=(
                "apps.reports.tasks.generate_report"
            ),
            kwargs={
                "tenant_id": "tenant-123",
                "report_type": "TASK_SUMMARY",
                "requested_by": "user-123",
            },
        )

class TestPhase6ExportFlow:

    @patch(
        "apps.common.async_service.AsyncJobDispatcher.dispatch_task"
    )
    def test_export_generation_is_async(
        self,
        dispatch_task,
    ):
        celery_result = MagicMock(
            id="export-job-123"
        )

        dispatch_task.return_value = (
            celery_result
        )

        result = (
            AsyncIntegrationService.generate_export(
                export_id="export-123"
            )
        )

        assert result.id == "export-job-123"

        dispatch_task.assert_called_once_with(
            task_name=(
                "apps.exports.tasks.generate_export"
            ),
            args=[
                "export-123",
            ],
        )

class TestPhase6RetryPolicy:

    def test_transient_error_is_retryable(self):

        policy = RetryPolicy(
            max_retries=5,
            base_delay=2,
            max_delay=300,
            jitter=False,
        )

        decision = policy.classify(
            TransientTaskError(
                "temporary failure"
            ),
            retries=0,
        )

        assert decision.should_retry is True
        assert decision.countdown == 2

    def test_retry_delay_grows_exponentially(self):

        policy = RetryPolicy(
            max_retries=5,
            base_delay=2,
            max_delay=300,
            jitter=False,
        )

        first = policy.calculate_delay(
            retries=0
        )

        second = policy.calculate_delay(
            retries=1
        )

        third = policy.calculate_delay(
            retries=2
        )

        assert first == 2
        assert second == 4
        assert third == 8

    def test_retry_delay_is_capped(self):

        policy = RetryPolicy(
            max_retries=10,
            base_delay=2,
            max_delay=10,
            jitter=False,
        )

        delay = policy.calculate_delay(
            retries=10
        )

        assert delay == 10

    def test_permanent_error_is_not_retryable(self):

        policy = RetryPolicy()

        decision = policy.classify(
            PermanentTaskError(
                "permanent failure"
            ),
            retries=0,
        )

        assert decision.should_retry is False

    def test_validation_error_is_not_retryable(self):

        policy = RetryPolicy()

        decision = policy.classify(
            ValidationTaskError(
                "invalid payload"
            ),
            retries=0,
        )

        assert decision.should_retry is False

    def test_authentication_error_is_not_retryable(self):

        policy = RetryPolicy()

        decision = policy.classify(
            AuthenticationTaskError(
                "authentication failed"
            ),
            retries=0,
        )

        assert decision.should_retry is False

    def test_retry_stops_after_max_retries(self):

        policy = RetryPolicy(
            max_retries=5
        )

        decision = policy.classify(
            TransientTaskError(
                "temporary failure"
            ),
            retries=5,
        )

        assert decision.should_retry is False

class TestPhase6TenantIsolation:

    @patch(
        "apps.common.async_service.dispatch_event"
    )
    def test_event_contains_correct_tenant(
        self,
        dispatch_event,
    ):
        dispatch_event.delay.return_value = (
            MagicMock(id="job-123")
        )

        EventPublisher.task_completed(
            tenant_id="tenant-a",
            user_id="user-a",
            task_id="task-a",
            completed_by="user-a",
        )

        args = dispatch_event.delay.call_args.args

        assert args[2] == "tenant-a"

        assert args[4]["task_id"] == "task-a"

    @patch(
        "apps.common.async_service.dispatch_event"
    )
    def test_second_tenant_event_keeps_its_tenant_context(
        self,
        dispatch_event,
    ):
        dispatch_event.delay.return_value = (
            MagicMock(id="job-123")
        )

        EventPublisher.task_completed(
            tenant_id="tenant-b",
            user_id="user-b",
            task_id="task-b",
            completed_by="user-b",
        )

        args = dispatch_event.delay.call_args.args

        assert args[2] == "tenant-b"

        assert args[4]["task_id"] == "task-b"

class TestPhase6EventContract:

    def test_event_structure(self):

        event = AsyncEvent(
            event_id="event-123",
            event_type="TASK_COMPLETED",
            tenant_id="tenant-123",
            user_id="user-123",
            payload={
                "task_id": "task-123",
            },
        )

        assert event.event_id == "event-123"

        assert (
            event.event_type
            == "TASK_COMPLETED"
        )

        assert (
            event.tenant_id
            == "tenant-123"
        )

        assert (
            event.user_id
            == "user-123"
        )

        assert event.payload == {
            "task_id": "task-123",
        }