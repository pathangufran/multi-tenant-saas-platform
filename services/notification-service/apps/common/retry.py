import random
from __future__ import annotations
from dataclasses import dataclass

class RetryError(Exception):
    """Base exception for retry-related errors."""

class TransientTaskError(RetryError):
    """
    Error that is expected to be temporary.

    Examples:
    - network timeout
    - temporary external API failure
    - temporary database connectivity issue
    """

class PermanentTaskError(RetryError):
    """
    Error that should not be retried.

    Examples:
    - invalid request
    - invalid data
    - unsupported operation
    """

class ValidationTaskError(PermanentTaskError):
    """Validation failure that should not be retried."""

class AuthenticationTaskError(PermanentTaskError):
    """Authentication/authorization failure that should not be retried."""

@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    countdown: int
    reason: str

class RetryPolicy:
    """
    Centralized retry policy for Celery tasks.

    The policy uses exponential backoff with optional jitter.
    """

    def __init__(
        self,
        *,
        max_retries: int = 5,
        base_delay: int = 2,
        max_delay: int = 300,
        jitter: bool = True,
    ):
        if max_retries < 0:
            raise ValueError(
                "max_retries must be greater than or equal to zero."
            )

        if base_delay <= 0:
            raise ValueError(
                "base_delay must be greater than zero."
            )

        if max_delay <= 0:
            raise ValueError(
                "max_delay must be greater than zero."
            )

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def calculate_delay(
        self,
        *,
        retry_count: int,
    ) -> int:
        if retry_count < 0:
            raise ValueError(
                "retry_count cannot be negative."
            )

        delay = self.base_delay * (
            2 ** retry_count
        )

        delay = min(
            delay,
            self.max_delay,
        )

        if self.jitter:
            jitter_amount = random.randint(
                0,
                max(1, delay // 4),
            )

            delay += jitter_amount

        return min(
            delay,
            self.max_delay,
        )

    def classify(
        self,
        *,
        exception: Exception,
        retry_count: int,
    ) -> RetryDecision:

        if isinstance(
            exception,
            (
                PermanentTaskError,
                ValidationTaskError,
                AuthenticationTaskError,
            ),
        ):
            return RetryDecision(
                should_retry=False,
                countdown=0,
                reason="permanent_error",
            )

        if isinstance(
            exception,
            TransientTaskError,
        ):
            if retry_count >= self.max_retries:
                return RetryDecision(
                    should_retry=False,
                    countdown=0,
                    reason="max_retries_exceeded",
                )

            return RetryDecision(
                should_retry=True,
                countdown=self.calculate_delay(
                    retry_count=retry_count,
                ),
                reason="transient_error",
            )

        return RetryDecision(
            should_retry=False,
            countdown=0,
            reason="unknown_error",
        )