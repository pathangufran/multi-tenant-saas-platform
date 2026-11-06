import random
from django.conf import settings

class RetryPolicy:
    
    @staticmethod
    def should_retry(attempt):
        return attempt < settings.KAFKA_MAX_RETRIES
    
    @staticmethod
    def get_delay(attempt):
        base_delay = settings.KAFKA_RETRY_BASE_DELAY
        max_delay = settings.KAFKA_RETRY_MAX_DELAY
        jitter = settings.KAFKA_RETRY_JITTER

        exponential_delay = (
            base_delay * (2 ** (attempt - 1))
        )

        delay = min(
            exponential_delay,max_delay,
        )

        jitter_value = random.uniform(
            0,
            delay * jitter,
        )

        return delay + jitter_value