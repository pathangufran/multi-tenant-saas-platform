from __future__ import annotations
from celery import shared_task
from .retry import (
    RetryPolicy,
    TransientTaskError,
)
from .task_infrastructure import BaseTask

@shared_task(
    bind=True,
    base=BaseTask,
    name="apps.common.tasks.health_check_task",
)
def health_check_task(self):
    """
    Basic Celery worker health check.
    """

    context = self.build_context()

    self.log_start(context)

    result = {
        "status": "ok",
        "task": self.name,
    }

    self.log_success(
        context,
        result=result,
    )

    return result

@shared_task(
    bind=True,
    base=BaseTask,
    name="apps.common.tasks.idempotent_task",
)
def idempotent_task(
    self,
    operation_id: str,
):
    """
    Demonstrates the idempotency foundation.

    Only the first execution for a given operation_id
    performs the operation.
    """

    context = self.build_context()

    self.log_start(
        context,
        operation_id=operation_id,
    )

    idempotency_key, acquired = (
        self.acquire_idempotency(
            operation="common-task",
            identifier=operation_id,
        )
    )

    if not acquired:
        self.log_success(
            context,
            operation_id=operation_id,
            skipped=True,
        )

        return {
            "status": "already_processed",
            "operation_id": operation_id,
        }

    try:
        result = {
            "status": "processed",
            "operation_id": operation_id,
        }

        self.log_success(
            context,
            operation_id=operation_id,
        )

        return result

    except Exception as exc:
        self.release_idempotency(
            idempotency_key,
        )
        self.log_failure(
            context,
            exc,
            operation_id=operation_id,
        )
        raise

@shared_task(
    bind=True,
    base=BaseTask,
    name="apps.common.tasks.retryable_task",
    max_retries=5,
)
def retryable_task(
    self,
    attempt_name: str,
    *,
    fail: bool = False,
):
    """
    Demonstrates the centralized retry policy.

    This task intentionally raises a transient error when
    fail=True so the retry mechanism can be exercised.
    """

    context = self.build_context()

    self.log_start(
        context,
        attempt_name=attempt_name,
        retry_count=self.request.retries,
    )

    policy = RetryPolicy(
        max_retries=self.max_retries,
    )

    try:
        if fail:
            raise TransientTaskError(
                "Temporary task failure."
            )

        result = {
            "status": "processed",
            "attempt_name": attempt_name,
            "retry_count": self.request.retries,
        }

        self.log_success(
            context,
            **result,
        )

        return result

    except Exception as exc:

        decision = policy.classify(
            exception=exc,
            retry_count=self.request.retries,
        )
        self.log_failure(
            context,
            exc,
            attempt_name=attempt_name,
            retry_count=self.request.retries,
            retry_reason=decision.reason,
            should_retry=decision.should_retry,
            countdown=decision.countdown,
        )

        if not decision.should_retry:
            raise

        raise self.retry(
            exc=exc,
            countdown=decision.countdown,
        )