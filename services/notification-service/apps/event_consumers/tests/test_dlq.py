import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from apps.event_consumers.dlq import DeadLetterPublisher

class DeadLetterPublisherTests(SimpleTestCase):

    def setUp(self):
        self.failed_event = SimpleNamespace(
            event_id=uuid.uuid4(),
            event_type="task.assigned",
            topic="saas.events.v1",
            partition=0,
            offset=10,
            attempts=5,
            error_message="Handler failed",
            original_payload={
                "event_id": str(uuid.uuid4()),
                "event_type": "task.assigned",
            },
        )

        self.producer = MagicMock()
        self.producer.send.return_value.get.return_value = None

    @patch(
        "apps.event_consumers.dlq.FailedEventService.mark_published"
    )
    def test_publish_sends_event_to_dlq(self, mock_mark_published):
        publisher = DeadLetterPublisher(
            producer=self.producer,
        )

        publisher.publish(self.failed_event)

        self.producer.send.assert_called_once()
        args, kwargs = self.producer.send.call_args

        self.assertEqual(args[0], "saas.events.dlq.v1")
        self.assertEqual(
            kwargs["key"],
            str(self.failed_event.event_id).encode("utf-8"),
        )

        payload = kwargs["value"]

        self.assertEqual(payload["dlq_version"], 1)
        self.assertEqual(
            payload["event"],
            self.failed_event.original_payload,
        )

        mock_mark_published.assert_called_once_with(
            self.failed_event
        )

    @patch(
        "apps.event_consumers.dlq.FailedEventService.mark_published"
    )
    @patch(
        "apps.event_consumers.dlq.FailedEventService.mark_publish_failed"
    )
    def test_publish_failure_is_recorded(
        self,
        mock_mark_failed,
        mock_mark_published,
    ):
        self.producer.send.return_value.get.side_effect = RuntimeError(
            "Kafka unavailable"
        )

        publisher = DeadLetterPublisher(
            producer=self.producer,
        )

        with self.assertRaises(RuntimeError):
            publisher.publish(self.failed_event)

        mock_mark_failed.assert_called_once()
        mock_mark_published.assert_not_called()