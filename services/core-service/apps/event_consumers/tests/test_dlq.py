import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from apps.event_consumers.dlq import DeadLetterPublisher
from apps.event_consumers.models import FailedEvent

@override_settings(
    KAFKA_DLQ_TOPIC="saas.events.dlq.v1",
    KAFKA_CONSUMER_GROUP="core-service-v1",
)
class DeadLetterPublisherTests(TestCase):

    def setUp(self):

        self.event_id = uuid.uuid4()

        self.failed_event = FailedEvent.objects.create(
            event_id=self.event_id,
            event_type="project.created",
            topic="saas.events.v1",
            partition=1,
            offset=100,
            attempts=5,
            error_message="Handler execution failed",
            original_payload={
                "event_id": str(self.event_id),
                "event_type": "project.created",
                "data": {
                    "project_id": str(uuid.uuid4()),
                },
            },
        )

        self.producer = Mock()

        self.metadata = SimpleNamespace(
            topic="saas.events.dlq.v1",
            partition=2,
            offset=50,
        )

        self.future = Mock()
        self.future.get.return_value = self.metadata

        self.producer.send.return_value = self.future

        self.publisher = DeadLetterPublisher(
            producer=self.producer
        )

    def test_build_dlq_payload(self):

        payload = self.publisher.build_payload(
            self.failed_event
        )

        self.assertEqual(
            payload["dlq_version"],
            1,
        )

        self.assertEqual(
            payload["source"]["topic"],
            "saas.events.v1",
        )

        self.assertEqual(
            payload["source"]["partition"],
            1,
        )

        self.assertEqual(
            payload["source"]["offset"],
            100,
        )

        self.assertEqual(
            payload["source"]["consumer_group"],
            "core-service-v1",
        )

        self.assertEqual(
            payload["failure"]["attempts"],
            5,
        )

        self.assertEqual(
            payload["original_event"],
            self.failed_event.original_payload,
        )

    def test_publish_event_to_dlq(self):

        result = self.publisher.publish(
            self.failed_event
        )

        self.producer.send.assert_called_once()

        call_kwargs = self.producer.send.call_args.kwargs

        self.assertEqual(
            call_kwargs["key"],
            str(self.event_id),
        )

        self.assertEqual(
            call_kwargs["value"]["original_event"],
            self.failed_event.original_payload,
        )

        self.future.get.assert_called_once_with(
            timeout=15
        )

        self.failed_event.refresh_from_db()

        self.assertEqual(
            self.failed_event.status,
            FailedEvent.Status.PUBLISHED,
        )

        self.assertIsNotNone(
            self.failed_event.dlq_published_at
        )

        self.assertEqual(
            result["status"],
            "PUBLISHED",
        )

        self.assertEqual(
            result["topic"],
            "saas.events.dlq.v1",
        )

    def test_publish_failure_updates_failed_event(self):

        self.future.get.side_effect = RuntimeError(
            "Kafka broker unavailable"
        )

        with self.assertRaises(RuntimeError):
            self.publisher.publish(
                self.failed_event
            )

        self.failed_event.refresh_from_db()

        self.assertEqual(
            self.failed_event.status,
            FailedEvent.Status.FAILED,
        )

        self.assertIn(
            "Kafka broker unavailable",
            self.failed_event.error_message,
        )

        self.assertIsNone(
            self.failed_event.dlq_published_at
        )

    def test_publish_uses_injected_producer(self):

        self.publisher.publish(self.failed_event)

        self.producer.send.assert_called_once()

        # An injected producer is not owned by this publisher.
        self.producer.close.assert_not_called()

    @patch(
        "apps.event_consumers.dlq.KafkaProducer"
    )
    def test_create_producer_configuration(
        self,
        mock_kafka_producer,
    ):

        with override_settings(
            KAFKA_BOOTSTRAP_SERVERS="kafka:29092"
        ):
            publisher = DeadLetterPublisher()

            publisher.create_producer()

        kwargs = mock_kafka_producer.call_args.kwargs

        self.assertEqual(
            kwargs["bootstrap_servers"],
            ["kafka:29092"],
        )

        self.assertEqual(
            kwargs["acks"],
            "all",
        )

        self.assertEqual(
            kwargs["retries"],
            5,
        )

    def test_owned_producer_is_closed_after_publish(self):

        publisher = DeadLetterPublisher()

        with patch.object(
            publisher,
            "create_producer",
            return_value=self.producer,
        ):
            publisher.publish(self.failed_event)

        self.producer.close.assert_called_once()