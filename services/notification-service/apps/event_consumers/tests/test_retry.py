from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.event_consumers.retry import RetryPolicy

@override_settings(
    KAFKA_MAX_RETRIES=5,
    KAFKA_RETRY_BASE_DELAY=1.0,
    KAFKA_RETRY_MAX_DELAY=30.0,
    KAFKA_RETRY_JITTER=0.25,
)
class RetryPolicyTests(SimpleTestCase):

    def test_retry_allowed_before_max_attempts(self):
        self.assertTrue(RetryPolicy.should_retry(1))
        self.assertTrue(RetryPolicy.should_retry(4))

    def test_retry_not_allowed_at_max_attempts(self):
        self.assertFalse(RetryPolicy.should_retry(5))

    @patch("apps.event_consumers.retry.random.uniform")
    def test_exponential_backoff(self, mock_uniform):
        mock_uniform.return_value = 0

        self.assertEqual(RetryPolicy.get_delay(1), 1.0)
        self.assertEqual(RetryPolicy.get_delay(2), 2.0)
        self.assertEqual(RetryPolicy.get_delay(3), 4.0)

    @patch("apps.event_consumers.retry.random.uniform")
    def test_backoff_is_capped(self, mock_uniform):
        mock_uniform.return_value = 0

        self.assertEqual(RetryPolicy.get_delay(10), 30.0)

    @patch("apps.event_consumers.retry.random.uniform")
    def test_jitter_is_added(self, mock_uniform):
        mock_uniform.return_value = 0.2

        self.assertAlmostEqual(
            RetryPolicy.get_delay(1),
            1.2,
        )