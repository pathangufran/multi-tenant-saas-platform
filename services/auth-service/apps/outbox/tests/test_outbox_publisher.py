import uuid
from unittest.mock import MagicMock, patch
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.outbox.models import OutboxEvent
from apps.outbox.publisher import (
    OutboxPublisher,
    build_event_envelope,
    build_partition_key,
)
from apps.outbox.services import OutboxService

@override_settings(
    KAFKA_BOOTSTRAP_SERVERS=["localhost:9092"],
    KAFKA_EVENTS_TOPIC="saas.events.v1",
)
class OutboxPublisherTests(TestCase):

    def create_event(self, tenant_id=None):
        with transaction.atomic():
            return OutboxService.record_event(
                event_type="user.registered",
                aggregate_type="user",
                aggregate_id=str(uuid.uuid4()),
                aggregate_version=1,
                tenant_id=tenant_id,
                data={
                    "email": "test@example.com",
                },
            )

    def test_build_partition_key_for_platform_event(self):
        event = self.create_event()

        key = build_partition_key(event)

        self.assertEqual(
            key,
            f"user:{event.aggregate_id}",
        )

    def test_build_partition_key_for_tenant_event(self):
        tenant_id = uuid.uuid4()
        event = self.create_event(tenant_id=tenant_id)

        key = build_partition_key(event)

        self.assertEqual(
            key,
            f"{tenant_id}:user:{event.aggregate_id}",
        )

    def test_build_event_envelope(self):
        event = self.create_event()

        payload = build_event_envelope(event)

        self.assertEqual(
            payload["event_id"],
            str(event.event_id),
        )

        self.assertEqual(
            payload["event_type"],
            "user.registered",
        )

        self.assertEqual(
            payload["producer"],
            "auth-service",
        )

        self.assertEqual(
            payload["aggregate_version"],
            1,
        )

        self.assertIn("correlation_id", payload)
        self.assertIn("occurred_at", payload)
        self.assertIn("data", payload)

    def test_claim_pending_events(self):
        self.create_event()

        events = OutboxPublisher.claim_pending_events()

        self.assertEqual(len(events), 1)

        event = OutboxEvent.objects.get(
            event_id=events[0].event_id,
        )

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )

        self.assertIsNotNone(event.lock_token)
        self.assertIsNotNone(event.locked_until)
        self.assertEqual(event.attempts, 1)

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_publish_batch_success(self, mock_producer_class):
        event = self.create_event()

        producer = MagicMock()
        producer.send.return_value.get.return_value = None

        mock_producer_class.return_value = producer

        result = OutboxPublisher.publish_batch()

        event.refresh_from_db()

        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["published"], 1)
        self.assertEqual(result["failed"], 0)

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PUBLISHED,
        )

        self.assertIsNotNone(event.published_at)

        producer.send.assert_called_once()
        producer.close.assert_called_once()

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_publish_batch_failure_returns_event_to_pending(
        self,
        mock_producer_class,
    ):
        event = self.create_event()

        producer = MagicMock()

        producer.send.return_value.get.side_effect = RuntimeError(
            "Kafka unavailable"
        )

        mock_producer_class.return_value = producer

        result = OutboxPublisher.publish_batch()

        event.refresh_from_db()

        self.assertEqual(result["claimed"], 1)
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["failed"], 1)

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )

        self.assertGreater(event.available_at, timezone.now())
        self.assertIn("Kafka unavailable", event.last_error)

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_empty_outbox_does_not_create_producer(
        self,
        mock_producer_class,
    ):
        result = OutboxPublisher.publish_batch()

        self.assertEqual(
            result,
            {
                "claimed": 0,
                "published": 0,
                "failed": 0,
            },
        )

        mock_producer_class.assert_not_called()

    def test_stale_lock_token_cannot_mark_event_published(self):
        event = self.create_event()

        claimed = OutboxPublisher.claim_pending_events()

        event.refresh_from_db()

        event.lock_token = uuid.uuid4()
        event.save(update_fields=["lock_token"])

        result = OutboxPublisher.mark_published(claimed[0])

        self.assertFalse(result)

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PROCESSING,
        )