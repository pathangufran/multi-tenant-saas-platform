import pytest
from apps.common.tasks import (
    health_check_task,
    idempotent_task,
    retryable_task,
)

class TestHealthCheckTask:

    def test_health_check(self):

        result = health_check_task.apply().get()

        assert result["status"] == "ok"

@pytest.mark.django_db
class TestIdempotentTask:

    def test_first_execution_is_processed(self):

        operation_id = "retry-test-operation"

        result = idempotent_task.apply(
            args=[operation_id],
        ).get()

        assert result == {
            "status": "processed",
            "operation_id": operation_id,
        }

    def test_second_execution_is_skipped(self):

        operation_id = (
            "retry-test-operation-duplicate"
        )

        first = idempotent_task.apply(
            args=[operation_id],
        ).get()

        second = idempotent_task.apply(
            args=[operation_id],
        ).get()

        assert first["status"] == "processed"

        assert (
            second["status"]
            == "already_processed"
        )

        assert (
            second["operation_id"]
            == operation_id
        )

class TestRetryableTask:

    def test_successful_execution(self):

        result = retryable_task.apply(
            args=["successful-task"],
            kwargs={
                "fail": False,
            },
        ).get()

        assert result["status"] == "processed"
        assert result["attempt_name"] == (
            "successful-task"
        )
        assert result["retry_count"] == 0