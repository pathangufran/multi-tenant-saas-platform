import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.outbox.models import OutboxEvent
from apps.outbox.publisher import (
    build_event_envelope,
    build_partition_key,
    claim_pending_events,
    mark_publish_failed,
    mark_published,
    publish_pending_events,
)

class OutboxPublisherTests(TestCase):

    def create_event(self, **overrides):
        values = {
            "event_type": "task.assigned",
            "producer": "core-service",
            "tenant_id": uuid.uuid4(),
            "aggregate_type": "task",
            "aggregate_id": "task-123",
            "aggregate_version": 1,
            "data": {"task_id": "task-123"},
        }

        values.update(overrides)

        return OutboxEvent.objects.create(**values)

    def test_partition_key_contains_tenant_and_aggregate(self):
        event = self.create_event()

        key = build_partition_key(event)

        self.assertEqual(
            key,
            f"{event.tenant_id}:task:task-123",
        )

    def test_platform_event_partition_key(self):
        event = self.create_event(
            tenant_id=None,
            aggregate_type="user",
            aggregate_id="user-123",
        )

        self.assertEqual(
            build_partition_key(event),
            "user:user-123",
        )

    def test_event_envelope_contains_required_fields(self):
        event = self.create_event()

        envelope = build_event_envelope(event)

        self.assertEqual(
            envelope["event_id"],
            str(event.event_id),
        )
        self.assertEqual(
            envelope["event_type"],
            "task.assigned",
        )
        self.assertEqual(
            envelope["producer"],
            "core-service",
        )
        self.assertEqual(
            envelope["data"],
            event.data,
        )
        self.assertIn("correlation_id", envelope)
        self.assertIn("occurred_at", envelope)

    def test_claim_pending_event(self):
        event = self.create_event()

        claimed = claim_pending_events()

        self.assertEqual(len(claimed), 1)

        claimed_event, token = claimed[0]

        self.assertEqual(claimed_event.event_id, event.event_id)
        self.assertIsNotNone(token)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )
        self.assertEqual(event.attempts, 1)
        self.assertEqual(event.lock_token, token)
        self.assertIsNotNone(event.locked_until)

    def test_claim_does_not_claim_future_events(self):
        self.create_event(
            available_at=timezone.now() + timedelta(hours=1),
        )

        self.assertEqual(claim_pending_events(), [])

    def test_expired_processing_event_can_be_reclaimed(self):
        event = self.create_event(
            status=OutboxEvent.Status.PROCESSING,
            locked_until=timezone.now() - timedelta(seconds=1),
            lock_token=uuid.uuid4(),
        )

        claimed = claim_pending_events()

        self.assertEqual(len(claimed), 1)

        claimed_event, token = claimed[0]

        self.assertEqual(claimed_event.event_id, event.event_id)
        self.assertNotEqual(token, None)

        event.refresh_from_db()

        self.assertEqual(event.lock_token, token)
        self.assertEqual(event.attempts, 1)

    def test_mark_published(self):
        event = self.create_event(
            status=OutboxEvent.Status.PROCESSING,
            lock_token=uuid.uuid4(),
        )

        result = mark_published(
            event.event_id,
            event.lock_token,
        )

        self.assertTrue(result)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PUBLISHED,
        )
        self.assertIsNotNone(event.published_at)
        self.assertIsNone(event.lock_token)

    def test_old_lock_token_cannot_mark_event_published(self):
        event = self.create_event(
            status=OutboxEvent.Status.PROCESSING,
            lock_token=uuid.uuid4(),
        )

        result = mark_published(
            event.event_id,
            uuid.uuid4(),
        )

        self.assertFalse(result)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )

    def test_mark_publish_failed_releases_event(self):
        token = uuid.uuid4()

        event = self.create_event(
            status=OutboxEvent.Status.PROCESSING,
            lock_token=token,
            attempts=2,
        )

        result = mark_publish_failed(
            event.event_id,
            token,
            "Kafka unavailable",
        )

        self.assertTrue(result)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )
        self.assertEqual(
            event.last_error,
            "Kafka unavailable",
        )
        self.assertIsNone(event.lock_token)
        self.assertIsNone(event.locked_until)
        self.assertGreater(event.available_at, timezone.now())

    def test_old_lock_token_cannot_release_event(self):
        event = self.create_event(
            status=OutboxEvent.Status.PROCESSING,
            lock_token=uuid.uuid4(),
        )

        result = mark_publish_failed(
            event.event_id,
            uuid.uuid4(),
            "Old publisher failure",
        )

        self.assertFalse(result)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )

    @override_settings(
        KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
    )
    @patch("apps.outbox.publisher.KafkaProducer")
    def test_publish_pending_event_successfully(
        self,
        mock_producer_class,
    ):
        event = self.create_event()

        mock_producer = MagicMock()
        mock_future = MagicMock()

        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        result = publish_pending_events()

        event.refresh_from_db()

        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["published"], 1)
        self.assertEqual(result["failed"], 0)

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PUBLISHED,
        )

        mock_producer.send.assert_called_once()
        mock_future.get.assert_called_once()
        mock_producer.close.assert_called_once()

    @override_settings(
        KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
    )
    @patch("apps.outbox.publisher.KafkaProducer")
    def test_publish_failure_releases_event(
        self,
        mock_producer_class,
    ):
        event = self.create_event()

        mock_producer = MagicMock()
        mock_future = MagicMock()

        mock_future.get.side_effect = RuntimeError(
            "Kafka broker unavailable"
        )

        mock_producer.send.return_value = mock_future
        mock_producer_class.return_value = mock_producer

        result = publish_pending_events()

        event.refresh_from_db()

        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["failed"], 1)

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )
        self.assertIn(
            "Kafka broker unavailable",
            event.last_error,
        )

    @override_settings(
        KAFKA_BOOTSTRAP_SERVERS=""
    )
    def test_missing_kafka_configuration_releases_claimed_events(self):
        event = self.create_event()

        result = publish_pending_events()

        event.refresh_from_db()

        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["failed"], 1)

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )

    def test_empty_outbox_does_not_create_producer(self):
        with patch(
            "apps.outbox.publisher.KafkaProducer"
        ) as mock_producer:
            result = publish_pending_events()

        self.assertEqual(result["claimed"], 0)
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["failed"], 0)

        mock_producer.assert_not_called()
