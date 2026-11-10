import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from apps.event_consumers.consumer import CoreEventConsumer
from apps.event_consumers.exceptions import (
    EventProcessingError,
    InvalidEventError,
)

@override_settings(
    KAFKA_MAX_RETRIES=3,
    KAFKA_RETRY_BASE_DELAY=2,
    KAFKA_RETRY_MAX_DELAY=60,
    KAFKA_RETRY_JITTER=False,
)
class CoreEventConsumerTests(TestCase):

    def setUp(self):

        self.kafka_consumer = Mock()
        self.dlq_publisher = Mock()

        self.consumer = CoreEventConsumer(
            consumer=self.kafka_consumer,
            dlq_publisher=self.dlq_publisher,
        )

        self.event_id = str(uuid.uuid4())

        self.event = {
            "event_id": self.event_id,
            "event_type": "project.created",
            "event_version": 1,
            "occurred_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "producer": "core-service",
            "tenant_id": str(uuid.uuid4()),
            "aggregate_type": "project",
            "aggregate_id": str(uuid.uuid4()),
            "aggregate_version": 1,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": "",
            "data": {
                "project_id": str(uuid.uuid4()),
                "name": "Test Project",
            },
        }

        self.message = SimpleNamespace(
            value=self.event,
            topic="saas.events.v1",
            partition=0,
            offset=10,
        )

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_successful_event_is_committed(
        self,
        mock_process,
    ):

        mock_process.return_value = {
            "status": "PROCESSED",
            "event_id": self.event_id,
        }

        result = self.consumer.handle_message(
            self.message
        )

        self.assertEqual(
            result["status"],
            "PROCESSED",
        )

        self.kafka_consumer.commit.assert_called_once()

        self.dlq_publisher.publish.assert_not_called()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_duplicate_event_is_committed(
        self,
        mock_process,
    ):

        mock_process.return_value = {
            "status": "DUPLICATE",
            "event_id": self.event_id,
        }

        result = self.consumer.handle_message(
            self.message
        )

        self.assertEqual(
            result["status"],
            "DUPLICATE",
        )

        self.kafka_consumer.commit.assert_called_once()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_ignored_event_is_committed(
        self,
        mock_process,
    ):

        mock_process.return_value = {
            "status": "IGNORED",
            "event_id": self.event_id,
        }

        result = self.consumer.handle_message(
            self.message
        )

        self.assertEqual(
            result["status"],
            "IGNORED",
        )

        self.kafka_consumer.commit.assert_called_once()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    @patch(
        "apps.event_consumers.consumer.FailedEventService.record_failure"
    )
    def test_invalid_event_is_sent_to_dlq(
        self,
        mock_record_failure,
        mock_process,
    ):

        mock_process.side_effect = InvalidEventError(
            "Invalid event envelope"
        )

        mock_record_failure.return_value = Mock()

        self.dlq_publisher.publish.return_value = {
            "status": "PUBLISHED",
            "event_id": self.event_id,
        }

        result = self.consumer.handle_message(
            self.message
        )

        self.assertEqual(
            result["status"],
            "DLQ_PUBLISHED",
        )

        mock_process.assert_called_once()

        mock_record_failure.assert_called_once()

        self.kafka_consumer.commit.assert_called_once()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    @patch(
        "apps.event_consumers.consumer.FailedEventService.record_failure"
    )
    @patch(
        "apps.event_consumers.consumer.time.sleep"
    )
    def test_failed_event_is_retried_then_sent_to_dlq(
        self,
        mock_sleep,
        mock_record_failure,
        mock_process,
    ):

        mock_process.side_effect = EventProcessingError(
            "Database unavailable"
        )

        mock_record_failure.return_value = Mock()

        self.dlq_publisher.publish.return_value = {
            "status": "PUBLISHED",
            "event_id": self.event_id,
        }

        result = self.consumer.handle_message(
            self.message
        )

        self.assertEqual(
            result["status"],
            "DLQ_PUBLISHED",
        )

        self.assertEqual(
            mock_process.call_count,
            3,
        )

        self.assertEqual(
            mock_sleep.call_count,
            2,
        )

        mock_record_failure.assert_called_once()

        self.kafka_consumer.commit.assert_called_once()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    @patch(
        "apps.event_consumers.consumer.FailedEventService.record_failure"
    )
    def test_dlq_failure_does_not_commit_offset(
        self,
        mock_record_failure,
        mock_process,
    ):

        mock_process.side_effect = InvalidEventError(
            "Invalid event"
        )

        mock_record_failure.return_value = Mock()

        self.dlq_publisher.publish.side_effect = RuntimeError(
            "Kafka DLQ unavailable"
        )

        with self.assertRaises(RuntimeError):
            self.consumer.handle_message(
                self.message
            )

        self.kafka_consumer.commit.assert_not_called()

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    @patch(
        "apps.event_consumers.consumer.FailedEventService.record_failure"
    )
    @patch(
        "apps.event_consumers.consumer.time.sleep"
    )
    def test_failure_recording_error_does_not_commit(
        self,
        mock_sleep,
        mock_record_failure,
        mock_process,
    ):

        mock_process.side_effect = EventProcessingError(
            "Database unavailable"
        )

        mock_record_failure.side_effect = RuntimeError(
            "PostgreSQL unavailable"
        )

        with self.assertRaises(RuntimeError):
            self.consumer.handle_message(
                self.message
            )

        self.kafka_consumer.commit.assert_not_called()

        self.dlq_publisher.publish.assert_not_called()

    def test_invalid_retry_configuration_is_rejected(self):

        with override_settings(KAFKA_MAX_RETRIES=0):

            with self.assertRaises(ValueError):
                self.consumer.handle_message(
                    self.message
                )

    def test_invalid_payload_gets_deterministic_event_id(self):

        self.message.value = {
            "event_id": "invalid-uuid",
            "event_type": "project.created",
        }

        first_id = self.consumer._get_failure_event_id(
            self.message.value,
            self.message,
        )

        second_id = self.consumer._get_failure_event_id(
            self.message.value,
            self.message,
        )

        self.assertEqual(first_id, second_id)

    def test_non_dictionary_payload_is_normalized(self):

        result = self.consumer._normalize_payload(
            "invalid-json-object"
        )

        self.assertEqual(
            result,
            {"raw_value": "invalid-json-object"},
        )

    def test_close_closes_consumer(self):

        self.consumer.close()

        self.kafka_consumer.close.assert_called_once()

    def test_stop_changes_running_state(self):

        self.consumer._running = True

        self.consumer.stop()

        self.assertFalse(self.consumer._running)