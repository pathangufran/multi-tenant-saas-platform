from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase,override_settings
from apps.event_consumers.consumer import NotificationEventConsumer

class NotificationEventConsumerTests(SimpleTestCase):

    def setUp(self):
        self.consumer = NotificationEventConsumer()
        self.consumer.consumer = MagicMock()

        self.message = SimpleNamespace(
            topic="saas.events.v1",
            partition=0,
            offset=10,
            value={
                "event_id": "test-event",
                "event_type": "task.assigned",
            },
        )

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_process_message_calls_processing_service(self, mock_process):
        mock_process.return_value = {
            "status": "PROCESSED",
            "event_id": "test-event",
        }

        result = self.consumer.process_message(self.message)

        self.assertEqual(result["status"], "PROCESSED")
        mock_process.assert_called_once_with(self.message.value)

    def test_commit_message_commits_consumer_offset(self):
        self.consumer.commit_message()

        self.consumer.consumer.commit.assert_called_once()

    @patch("apps.event_consumers.consumer.time.sleep")
    def test_retry_message_seeks_to_failed_offset(self, mock_sleep):
        self.consumer.retry_message(self.message)

        self.consumer.consumer.seek.assert_called_once()

        partition, offset = (
            self.consumer.consumer.seek.call_args.args
        )

        self.assertEqual(partition.topic, "saas.events.v1")
        self.assertEqual(partition.partition, 0)
        self.assertEqual(offset, 10)

        mock_sleep.assert_called_once_with(
            self.consumer.retry_delay
        )

    def test_close_closes_consumer(self):
        self.consumer.close()

        self.consumer.consumer.close.assert_called_once()
        self.assertIsNone(self.consumer.consumer)
        
@override_settings(
    KAFKA_MAX_RETRIES=3,
)
class ConsumerRetryTests(SimpleTestCase):

    def setUp(self):
        self.consumer = NotificationEventConsumer()
        self.consumer.consumer = MagicMock()
        self.consumer.dlq_publisher = MagicMock()

        self.message = SimpleNamespace(
            topic="saas.events.v1",
            partition=0,
            offset=10,
            value={
                "event_id": "test-event",
                "event_type": "task.assigned",
            },
        )

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_successful_processing_commits_offset(
        self,
        mock_process,
    ):
        mock_process.return_value = {
            "status": "PROCESSED",
            "event_id": "test-event",
        }

        result = self.consumer.handle_message(self.message)

        self.assertEqual(result["status"], "PROCESSED")
        self.consumer.consumer.commit.assert_called_once()
        self.consumer.dlq_publisher.publish.assert_not_called()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    @patch(
        "apps.event_consumers.consumer.time.sleep"
    )
    def test_exhausted_retries_send_event_to_dlq(
        self,
        mock_sleep,
        mock_process,
    ):
        mock_process.side_effect = RuntimeError("Database unavailable")

        with patch.object(
            self.consumer,
            "send_to_dlq",
        ) as mock_send_to_dlq:

            result = self.consumer.handle_message(self.message)

        self.assertEqual(result["status"], "DLQ")
        self.assertEqual(mock_process.call_count, 3)
        mock_send_to_dlq.assert_called_once()
        self.consumer.consumer.commit.assert_not_called()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_invalid_event_goes_directly_to_dlq(
        self,
        mock_process,
    ):
        from apps.event_consumers.exceptions import InvalidEventError

        mock_process.side_effect = InvalidEventError("Invalid envelope")

        with patch.object(
            self.consumer,
            "send_to_dlq",
        ) as mock_send_to_dlq:

            result = self.consumer.handle_message(self.message)

        self.assertEqual(result["status"], "DLQ")
        self.assertEqual(mock_process.call_count, 1)
        mock_send_to_dlq.assert_called_once()