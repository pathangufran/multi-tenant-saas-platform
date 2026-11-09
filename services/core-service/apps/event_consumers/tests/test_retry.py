from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.event_consumers.retry import RetryPolicy

class RetryPolicyTests(SimpleTestCase):

    @override_settings(KAFKA_MAX_RETRIES=5)
    def test_should_retry_within_limit(self):

        self.assertTrue(
            RetryPolicy.should_retry(1)
        )

        self.assertTrue(
            RetryPolicy.should_retry(4)
        )

    @override_settings(KAFKA_MAX_RETRIES=5)
    def test_should_not_retry_after_limit(self):

        self.assertFalse(
            RetryPolicy.should_retry(5)
        )

    @override_settings(
        KAFKA_RETRY_BASE_DELAY=2,
        KAFKA_RETRY_MAX_DELAY=60,
        KAFKA_RETRY_JITTER=False,
    )
    def test_exponential_backoff(self):

        self.assertEqual(
            RetryPolicy.get_delay(1),
            2,
        )

        self.assertEqual(
            RetryPolicy.get_delay(2),
            4,
        )

        self.assertEqual(
            RetryPolicy.get_delay(3),
            8,
        )

    @override_settings(
        KAFKA_RETRY_BASE_DELAY=2,
        KAFKA_RETRY_MAX_DELAY=10,
        KAFKA_RETRY_JITTER=False,
    )
    def test_backoff_is_capped(self):

        self.assertEqual(
            RetryPolicy.get_delay(10),
            10,
        )

    @override_settings(
        KAFKA_RETRY_BASE_DELAY=2,
        KAFKA_RETRY_MAX_DELAY=60,
        KAFKA_RETRY_JITTER=True,
    )
    @patch("apps.event_consumers.retry.random.uniform")
    def test_jitter_is_applied(self, mock_uniform):

        mock_uniform.return_value = 1.5

        delay = RetryPolicy.get_delay(2)

        mock_uniform.assert_called_once_with(
            2.0,
            4,
        )

        self.assertEqual(delay, 1.5)