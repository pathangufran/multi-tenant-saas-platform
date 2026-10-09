import uuid
import pytest
from apps.failed_jobs.models import FailedJobs
from apps.failed_jobs.services import FailedJobService

pytestmark = pytest.mark.django_db

class TestFailedJobService:

    def test_record_failure_creates_failed_job(self):

        task_id = str(uuid.uuid4())
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        exception = ValueError(
            "Something went wrong."
        )

        failed_job = (
            FailedJobService.record_failure(
                task_id=task_id,
                task_name=(
                    "apps.common.tasks.retryable_task"
                ),
                exception=exception,
                retry_count=5,
                tenant_id=tenant_id,
                user_id=user_id,
                request_id="request-123",
                traceback="traceback-content",
                task_args=[
                    "operation-123",
                ],
                task_kwargs={
                    "fail": True,
                },
                metadata={
                    "max_retries": 5,
                },
            )
        )

        assert failed_job.id is not None

        assert failed_job.task_id == task_id

        assert (
            failed_job.task_name
            == "apps.common.tasks.retryable_task"
        )

        assert (
            failed_job.tenant_id
            == tenant_id
        )

        assert (
            failed_job.user_id
            == user_id
        )

        assert (
            failed_job.request_id
            == "request-123"
        )

        assert (
            failed_job.status
            == FailedJobs.Status.FAILED
        )

        assert failed_job.retry_count == 5

        assert (
            failed_job.exception_type
            == "builtins.ValueError"
        )

        assert (
            failed_job.error_message
            == "Something went wrong."
        )

        assert (
            failed_job.traceback
            == "traceback-content"
        )

        assert failed_job.task_args == [
            "operation-123",
        ]

        assert failed_job.task_kwargs == {
            "fail": True,
        }

        assert failed_job.metadata == {
            "max_retries": 5,
        }

    def test_list_failures_returns_latest_first(self):

        tenant_id = uuid.uuid4()

        first = (
            FailedJobService.record_failure(
                task_id="task-1",
                task_name="task.one",
                exception=ValueError("first"),
                retry_count=5,
                tenant_id=tenant_id,
            )
        )

        second = (
            FailedJobService.record_failure(
                task_id="task-2",
                task_name="task.two",
                exception=ValueError("second"),
                retry_count=5,
                tenant_id=tenant_id,
            )
        )

        failures = list(
            FailedJobService.list_failures(
                tenant_id=tenant_id,
            )
        )

        assert len(failures) == 2

        assert failures[0].id == second.id

        assert failures[1].id == first.id

    def test_list_failures_filters_by_tenant(self):

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        FailedJobService.record_failure(
            task_id="task-a",
            task_name="task.one",
            exception=ValueError("tenant a"),
            tenant_id=tenant_a,
        )

        FailedJobService.record_failure(
            task_id="task-b",
            task_name="task.two",
            exception=ValueError("tenant b"),
            tenant_id=tenant_b,
        )

        failures = list(
            FailedJobService.list_failures(
                tenant_id=tenant_a,
            )
        )

        assert len(failures) == 1

        assert failures[0].task_id == "task-a"

    def test_list_failures_filters_by_task_name(self):

        FailedJobService.record_failure(
            task_id="task-1",
            task_name="tasks.email",
            exception=ValueError("email failed"),
        )

        FailedJobService.record_failure(
            task_id="task-2",
            task_name="tasks.report",
            exception=ValueError("report failed"),
        )

        failures = list(
            FailedJobService.list_failures(
                task_name="tasks.email",
            )
        )

        assert len(failures) == 1

        assert (
            failures[0].task_name
            == "tasks.email"
        )

    def test_list_failures_filters_by_status(self):

        failed_job = (
            FailedJobService.record_failure(
                task_id="task-1",
                task_name="tasks.email",
                exception=ValueError("failed"),
            )
        )

        FailedJobService.resolve_failure(
            failure_id=failed_job.id,
            resolution_notes="Investigated.",
        )

        resolved = list(
            FailedJobService.list_failures(
                status=FailedJobs.Status.RESOLVED,
            )
        )

        assert len(resolved) == 1

        assert resolved[0].id == failed_job.id

    def test_get_failure_returns_failure(self):

        failed_job = (
            FailedJobService.record_failure(
                task_id="task-1",
                task_name="tasks.email",
                exception=ValueError("failed"),
            )
        )

        result = (
            FailedJobService.get_failure(
                failure_id=failed_job.id,
            )
        )

        assert result.id == failed_job.id

    def test_resolve_failure_marks_job_resolved(self):

        failed_job = (
            FailedJobService.record_failure(
                task_id="task-1",
                task_name="tasks.email",
                exception=ValueError("failed"),
            )
        )

        resolved = (
            FailedJobService.resolve_failure(
                failure_id=failed_job.id,
                resolution_notes=(
                    "External provider recovered."
                ),
            )
        )

        assert (
            resolved.status
            == FailedJobs.Status.RESOLVED
        )

        assert (
            resolved.resolved_at
            is not None
        )

        assert (
            resolved.resolution_notes
            == "External provider recovered."
        )

    def test_platform_failure_can_have_no_tenant(self):

        failed_job = (
            FailedJobService.record_failure(
                task_id="platform-task",
                task_name="platform.cleanup",
                exception=RuntimeError(
                    "Platform cleanup failed."
                ),
            )
        )

        assert failed_job.tenant_id is None

        assert failed_job.user_id is None