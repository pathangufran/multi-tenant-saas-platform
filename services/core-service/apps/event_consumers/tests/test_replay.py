import uuid
from unittest.mock import Mock
from django.test import TestCase
from apps.event_consumers.models import FailedEvent
from apps.event_consumers.replay import FailedEventReplayService

class FailedEventReplayTests(TestCase):

    def setUp(self):

        self.event_id = uuid.uuid4()

        self.original_event = {
            "event_id": str(self.event_id),
            "event_type": "tenant.created",
            "event_version": 1,
            "producer": "tenant-service",
            "tenant_id": str(uuid.uuid4()),
            "aggregate_type": "tenant",
            "aggregate_id": str(uuid.uuid4()),
            "aggregate_version": 1,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": "",
            "data": {
                "tenant_id": str(uuid.uuid4()),
                "status": "ACTIVE",
            },
        }

        self.failed_event = FailedEvent.objects.create(
            event_id=self.event_id,
            event_type="tenant.created",
            topic="saas.events.v1",
            partition=0,
            offset=10,
            attempts=5,
            error_message="Processing failed",
            original_payload=self.original_event,
            status=FailedEvent.Status.PUBLISHED,
        )

        self.producer = Mock()
        self.producer.send.return_value.get.return_value = Mock()

    def test_replay_publishes_original_event(self):

        result = FailedEventReplayService.replay_event(
            self.failed_event.id,
            producer=self.producer,
        )

        self.assertEqual(result["status"], "REPLAYED")

        self.producer.send.assert_called_once()

        self.failed_event.refresh_from_db()

        self.assertEqual(
            self.failed_event.status,
            FailedEvent.Status.REPLAYED,
        )

        self.assertEqual(self.failed_event.replay_count, 1)

    def test_replayed_event_cannot_be_replayed_again(self):

        self.failed_event.status = FailedEvent.Status.REPLAYED
        self.failed_event.save(update_fields=["status"])

        result = FailedEventReplayService.replay_event(
            self.failed_event.id,
            producer=self.producer,
        )

        self.assertEqual(
            result["status"],
            "ALREADY_REPLAYED",
        )

        self.producer.send.assert_not_called()

    def test_pending_event_cannot_be_replayed(self):

        self.failed_event.status = FailedEvent.Status.PENDING
        self.failed_event.save(update_fields=["status"])

        with self.assertRaises(ValueError):
            FailedEventReplayService.replay_event(
                self.failed_event.id,
                producer=self.producer,
            )

        self.producer.send.assert_not_called()

    def test_replay_failure_preserves_failure_record(self):

        self.producer.send.side_effect = RuntimeError(
            "Kafka unavailable"
        )

        with self.assertRaises(RuntimeError):
            FailedEventReplayService.replay_event(
                self.failed_event.id,
                producer=self.producer,
            )

        self.failed_event.refresh_from_db()

        self.assertEqual(
            self.failed_event.status,
            FailedEvent.Status.PUBLISHED,
        )

        self.assertNotEqual(
            self.failed_event.last_replay_error,
            "",
        )