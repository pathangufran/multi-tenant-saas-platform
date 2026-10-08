import uuid
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
        
    def test_base_task_records_exhausted_failure():

        from unittest.mock import patch

        from apps.common.task_infrastructure import BaseTask
        from apps.failed_jobs.models import FailedJob

        task = BaseTask()

        task.name = "test.dead_letter_task"
        task.max_retries = 5

        with patch.object(
            task,
            "request",
            create=True,
        ) as request:

            request.retries = 5
            request.request_id = "request-123"
            request.tenant_id = uuid.uuid4()
            request.user_id = uuid.uuid4()

            exception = RuntimeError(
                "Permanent worker failure."
            )

            task.on_failure(
                exception,
                "celery-task-123",
                ("operation-1",),
                {"example": True},
                "traceback",
            )

        failed_job = FailedJob.objects.get(
            task_id="celery-task-123",
        )

        assert (
            failed_job.task_name
            == "test.dead_letter_task"
        )

        assert failed_job.retry_count == 5

        assert (
            failed_job.error_message
            == "Permanent worker failure."
        )

        assert (
            failed_job.request_id
            == "request-123"
        )