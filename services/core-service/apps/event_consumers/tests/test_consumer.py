from types import SimpleNamespace
from unittest.mock import Mock
from django.test import SimpleTestCase
from kafka import TopicPartition
from kafka.structs import OffsetAndMetadata
from apps.event_consumers.consumer import CoreEventConsumer

class CoreConsumerReliabilityTests(SimpleTestCase):

    def setUp(self):
        self.kafka_consumer = Mock()
        self.dlq_publisher = Mock()

        self.consumer = CoreEventConsumer(
            consumer=self.kafka_consumer,
            dlq_publisher=self.dlq_publisher,
        )

    def test_commit_uses_exact_message_offset(self):

        message = SimpleNamespace(
            topic="saas.events.v1",
            partition=2,
            offset=41,
        )

        self.consumer.commit_message(message)

        self.kafka_consumer.commit.assert_called_once_with(
            offsets={
                TopicPartition("saas.events.v1", 2):
                OffsetAndMetadata(42, ""),
            }
        )

    def test_invalid_json_is_rejected(self):

        message = SimpleNamespace(
            value=b"{invalid-json",
        )

        with self.assertRaises(ValueError):
            self.consumer.deserialize_message(message)

    def test_non_object_json_is_rejected(self):

        message = SimpleNamespace(
            value=b'["not", "an", "event"]',
        )

        with self.assertRaises(ValueError):
            self.consumer.deserialize_message(message)

    def test_valid_json_object_is_deserialized(self):

        message = SimpleNamespace(
            value=b'{"event_type": "tenant.created"}',
        )

        result = self.consumer.deserialize_message(message)

        self.assertEqual(
            result,
            {"event_type": "tenant.created"},
        )