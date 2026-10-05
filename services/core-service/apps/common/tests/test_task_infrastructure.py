import pytest
import logging
from django.core.cache import cache
from apps.common.tasks import (
    health_check_task,
    idempotent_task,
)
from apps.common.task_infrastructure import (
    BaseTask,
    PermanentTaskError,
    TaskExecutionContext,
    TaskIdempotency,
    TransientTaskError,
)

@pytest.fixture(autouse=True)
def clear_task_idempotency():
    cache.clear()
    yield
    cache.clear()

class TestTaskExecutionContext:

    def test_context_contains_task_metadata(self):
        context = TaskExecutionContext(
            task_id="task-123",
            task_name="test.task",
            request_id="request-123",
            tenant_id="tenant-123",
            user_id="user-123",
        )

        assert context.task_id == "task-123"
        assert context.task_name == "test.task"
        assert context.request_id == "request-123"
        assert context.tenant_id == "tenant-123"
        assert context.user_id == "user-123"

class TestTaskIdempotency:

    def test_first_acquire_succeeds(self):
        result = TaskIdempotency.acquire(
            "operation-1",
            ttl=60,
        )

        assert result is True

    def test_second_acquire_fails(self):
        first = TaskIdempotency.acquire(
            "operation-1",
            ttl=60,
        )

        second = TaskIdempotency.acquire(
            "operation-1",
            ttl=60,
        )

        assert first is True
        assert second is False

    def test_release_allows_reacquisition(self):
        TaskIdempotency.acquire(
            "operation-1",
            ttl=60,
        )

        TaskIdempotency.release("operation-1")

        result = TaskIdempotency.acquire(
            "operation-1",
            ttl=60,
        )

        assert result is True

    def test_empty_key_is_rejected(self):
        with pytest.raises(ValueError):
            TaskIdempotency.acquire("")

    def test_idempotency_key_has_expected_prefix(self):
        key = TaskIdempotency._key("operation-1")

        assert key == "celery:idempotency:operation-1"

class TestBaseTask:

    def test_base_task_is_abstract(self):
        assert BaseTask.abstract is True

    def test_build_context(self):
        task = BaseTask()

        task.request.id = "task-123"

        context = task.build_context(
            request_id="request-123",
            tenant_id="tenant-123",
            user_id="user-123",
        )

        assert context.task_id == "task-123"
        assert context.task_name == task.name
        assert context.request_id == "request-123"
        assert context.tenant_id == "tenant-123"
        assert context.user_id == "user-123"

    def test_generate_idempotency_key(self):
        task = BaseTask()

        result = task.generate_idempotency_key(
            operation="email",
            identifier="123",
        )

        assert result == "email:123"

    def test_generate_idempotency_key_rejects_empty_operation(self):
        task = BaseTask()

        with pytest.raises(ValueError):
            task.generate_idempotency_key(
                operation="",
                identifier="123",
            )

    def test_generate_idempotency_key_rejects_empty_identifier(self):
        task = BaseTask()

        with pytest.raises(ValueError):
            task.generate_idempotency_key(
                operation="email",
                identifier="",
            )

class TestTaskExceptions:

    def test_permanent_task_error_is_task_infrastructure_error(self):
        error = PermanentTaskError()

        assert isinstance(error, Exception)

    def test_transient_task_error_is_task_infrastructure_error(self):
        error = TransientTaskError()

        assert isinstance(error, Exception)

class TestCeleryTasks:

    def test_health_check_task_is_registered(self):
        assert (
            health_check_task.name
            == "apps.common.tasks.health_check_task"
        )

    def test_health_check_task_runs(self):
        result = health_check_task.apply()

        assert result.successful()
        assert result.result == "Celery is working."

    def test_idempotent_task_processes_first_execution(self):
        result = idempotent_task.apply(
            args=("operation-123",),
        )

        assert result.successful()
        assert result.result == {
            "status": "processed",
            "operation_id": "operation-123",
        }

    def test_idempotent_task_skips_duplicate_execution(self):
        first = idempotent_task.apply(
            args=("operation-123",),
        )

        second = idempotent_task.apply(
            args=("operation-123",),
        )

        assert first.successful()
        assert second.successful()

        assert first.result == {
            "status": "processed",
            "operation_id": "operation-123",
        }

        assert second.result == {
            "status": "already_processed",
            "operation_id": "operation-123",
        }

    def test_different_operations_are_independent(self):
        first = idempotent_task.apply(
            args=("operation-1",),
        )

        second = idempotent_task.apply(
            args=("operation-2",),
        )

        assert first.result["status"] == "processed"
        assert second.result["status"] == "processed"

class TestTaskLogging:

    def test_health_check_task_logs_execution(
        self,
        caplog,
    ):
        with caplog.at_level(logging.INFO):
            result = health_check_task.apply()

        assert result.successful()

        messages = [
            record.message
            for record in caplog.records
        ]

        assert "celery_task_started" in messages
        assert "celery_task_completed" in messages