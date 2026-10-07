import pytest
from apps.common.retry import (
    AuthenticationTaskError,
    PermanentTaskError,
    RetryPolicy,
    TransientTaskError,
    ValidationTaskError,
)

class TestRetryPolicy:

    def test_transient_error_should_retry(self):

        policy = RetryPolicy(
            max_retries=5,
            base_delay=2,
            jitter=False,
        )

        decision = policy.classify(
            exception=TransientTaskError(
                "Temporary failure"
            ),
            retry_count=0,
        )

        assert decision.should_retry is True
        assert decision.countdown == 2
        assert decision.reason == "transient_error"

    def test_exponential_backoff(self):

        policy = RetryPolicy(
            max_retries=5,
            base_delay=2,
            jitter=False,
        )

        assert (
            policy.calculate_delay(
                retry_count=0,
            )
            == 2
        )

        assert (
            policy.calculate_delay(
                retry_count=1,
            )
            == 4
        )

        assert (
            policy.calculate_delay(
                retry_count=2,
            )
            == 8
        )

        assert (
            policy.calculate_delay(
                retry_count=3,
            )
            == 16
        )

    def test_delay_is_capped(self):

        policy = RetryPolicy(
            max_retries=10,
            base_delay=2,
            max_delay=10,
            jitter=False,
        )

        assert (
            policy.calculate_delay(
                retry_count=10,
            )
            == 10
        )

    def test_permanent_error_should_not_retry(self):

        policy = RetryPolicy(
            max_retries=5,
        )

        decision = policy.classify(
            exception=PermanentTaskError(
                "Permanent failure"
            ),
            retry_count=0,
        )

        assert decision.should_retry is False
        assert decision.countdown == 0
        assert decision.reason == "permanent_error"

    def test_validation_error_should_not_retry(self):

        policy = RetryPolicy(
            max_retries=5,
        )

        decision = policy.classify(
            exception=ValidationTaskError(
                "Invalid input"
            ),
            retry_count=0,
        )

        assert decision.should_retry is False
        assert decision.reason == "permanent_error"

    def test_authentication_error_should_not_retry(self):

        policy = RetryPolicy(
            max_retries=5,
        )

        decision = policy.classify(
            exception=AuthenticationTaskError(
                "Authentication failed"
            ),
            retry_count=0,
        )

        assert decision.should_retry is False
        assert decision.reason == "permanent_error"

    def test_max_retries_prevents_retry(self):

        policy = RetryPolicy(
            max_retries=5,
            jitter=False,
        )

        decision = policy.classify(
            exception=TransientTaskError(
                "Temporary failure"
            ),
            retry_count=5,
        )

        assert decision.should_retry is False
        assert decision.countdown == 0
        assert decision.reason == "max_retries_exceeded"

    def test_unknown_error_is_not_retried(self):

        policy = RetryPolicy(
            max_retries=5,
        )

        decision = policy.classify(
            exception=ValueError(
                "Unexpected error"
            ),
            retry_count=0,
        )

        assert decision.should_retry is False
        assert decision.reason == "unknown_error"

    def test_negative_retry_count_is_rejected(self):

        policy = RetryPolicy()

        with pytest.raises(
            ValueError,
            match="retry_count cannot be negative",
        ):
            policy.calculate_delay(
                retry_count=-1,
            )

    def test_invalid_max_retries_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="max_retries",
        ):
            RetryPolicy(
                max_retries=-1,
            )

    def test_invalid_base_delay_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="base_delay",
        ):
            RetryPolicy(
                base_delay=0,
            )

    def test_invalid_max_delay_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="max_delay",
        ):
            RetryPolicy(
                max_delay=0,
            )