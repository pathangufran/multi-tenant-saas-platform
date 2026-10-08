import pytest
from unittest.mock import patch
from apps.common.integration_tasks import (
    dispatch_event,
)
from apps.common.tasks import (
    health_check_task,
    idempotent_task,
    retryable_task,
)

class TestPhase6TaskExecution:

    def test_health_check_task(self):

        result = health_check_task.apply().get()

        assert result["status"] == "ok"

    def test_idempotent_task_first_execution(self):

        operation_id = "phase6-operation-001"

        result = idempotent_task.apply(
            kwargs={
                "operation_id": operation_id,
            }
        ).get()

        assert result == {
            "status": "processed",
            "operation_id": operation_id,
        }

    def test_idempotent_task_second_execution(
        self,
    ):

        operation_id = (
            "phase6-idempotency-operation"
        )

        first = idempotent_task.apply(
            kwargs={
                "operation_id": operation_id,
            }
        ).get()

        second = idempotent_task.apply(
            kwargs={
                "operation_id": operation_id,
            }
        ).get()

        assert first["status"] == "processed"

        assert (
            second["status"]
            == "already_processed"
        )

    def test_retryable_task_success(self):

        result = retryable_task.apply(
            kwargs={
                "operation_id": "phase6-retry-success",
                "fail": False,
            }
        ).get()

        assert result["status"] == "processed"

        assert (
            result["operation_id"]
            == "phase6-retry-success"
        )

    @patch(
        "apps.common.integration_tasks.AsyncEventDispatcher.dispatch"
    )
    def test_dispatch_event_task_execution(
        self,
        dispatch,
    ):

        dispatch.return_value = type(
            "Result",
            (),
            {
                "id": "notification-task-123",
            },
        )()

        result = dispatch_event.apply(
            kwargs={
                "event_id": "event-123",
                "event_type": "TASK_ASSIGNED",
                "tenant_id": "tenant-123",
                "user_id": "user-123",
                "payload": {
                    "task_id": "task-123",
                },
            }
        ).get()

        assert result == {
            "status": "dispatched",
            "event_id": "event-123",
            "event_type": "TASK_ASSIGNED",
            "task_id": "notification-task-123",
        }

        dispatch.assert_called_once()