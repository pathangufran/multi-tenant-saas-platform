import random
from django.conf import settings

class RetryPolicy:

    @staticmethod
    def should_retry(attempt):

        max_retries = getattr(
            settings,
            "KAFKA_MAX_RETRIES",
            5,
        )

        return attempt < max_retries

    @staticmethod
    def get_delay(attempt):

        base_delay = getattr(
            settings,
            "KAFKA_RETRY_BASE_DELAY",
            2,
        )

        max_delay = getattr(
            settings,
            "KAFKA_RETRY_MAX_DELAY",
            60,
        )

        jitter = getattr(
            settings,
            "KAFKA_RETRY_JITTER",
            True,
        )

        delay = min(
            base_delay * (2 ** (attempt - 1)),
            max_delay,
        )

        if jitter:
            delay = random.uniform(
                delay * 0.5,
                delay,
            )

        return delay