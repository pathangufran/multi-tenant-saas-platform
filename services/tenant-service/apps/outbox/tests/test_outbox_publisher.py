import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.db import transaction
from django.utils import timezone
from apps.outbox.models import OutboxEvent
from apps.outbox.services import OutboxService
from apps.outbox.publisher import OutboxPublisher

@pytest.mark.django_db
class TestOutboxPublisher:

    def create_event(self):
        with transaction.atomic():
            return OutboxService.record_event(
                event_type="tenant.created",
                aggregate_type="tenant",
                aggregate_id="tenant-123",
                tenant_id="11111111-1111-4111-8111-111111111111",
                aggregate_version=1,
                data={
                    "tenant_id": "11111111-1111-4111-8111-111111111111",
                    "name": "Acme",
                },
            )

    def test_partition_key_includes_tenant_and_aggregate(self):
        event = self.create_event()

        key = OutboxPublisher._partition_key(event)

        assert key == (
            "11111111-1111-4111-8111-111111111111:"
            "tenant:tenant-123"
        )

    def test_serialized_event_contains_envelope_fields(self):
        event = self.create_event()

        payload = OutboxPublisher._serialize_event(event)

        assert payload["event_id"] == str(event.event_id)
        assert payload["event_type"] == "tenant.created"
        assert payload["event_version"] == 1
        assert payload["producer"] == "tenant-service"
        assert payload["aggregate_type"] == "tenant"
        assert payload["aggregate_id"] == "tenant-123"
        assert payload["aggregate_version"] == 1
        assert payload["data"]["name"] == "Acme"

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_publish_marks_event_as_published(
        self,
        kafka_producer_class,
    ):
        event = self.create_event()

        producer = MagicMock()
        future = MagicMock()
        future.get.return_value = None
        producer.send.return_value = future

        kafka_producer_class.return_value = producer

        stats = OutboxPublisher.publish_pending_events()

        event.refresh_from_db()

        assert stats["claimed"] == 1
        assert stats["published"] == 1
        assert stats["failed"] == 0

        assert event.status == OutboxEvent.Status.PUBLISHED
        assert event.published_at is not None
        assert event.lock_token is None
        assert event.locked_until is None

        producer.send.assert_called_once()
        producer.close.assert_called_once()

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_publish_failure_schedules_retry(
        self,
        kafka_producer_class,
    ):
        event = self.create_event()

        producer = MagicMock()
        future = MagicMock()
        future.get.side_effect = TimeoutError(
            "Kafka acknowledgement timeout"
        )
        producer.send.return_value = future

        kafka_producer_class.return_value = producer

        stats = OutboxPublisher.publish_pending_events()

        event.refresh_from_db()

        assert stats["claimed"] == 1
        assert stats["published"] == 0
        assert stats["failed"] == 1

        assert event.status == OutboxEvent.Status.PENDING
        assert event.published_at is None
        assert event.lock_token is None
        assert event.locked_until is None
        assert "Kafka acknowledgement timeout" in event.last_error

        assert event.available_at > timezone.now()
        producer.close.assert_called_once()

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_future_scheduled_event_is_not_claimed(
        self,
        kafka_producer_class,
    ):
        event = self.create_event()

        OutboxEvent.objects.filter(
            event_id=event.event_id,
        ).update(
            available_at=timezone.now() + timedelta(hours=1),
        )

        producer = MagicMock()
        kafka_producer_class.return_value = producer

        stats = OutboxPublisher.publish_pending_events()

        event.refresh_from_db()

        assert stats["claimed"] == 0
        assert stats["published"] == 0
        assert event.status == OutboxEvent.Status.PENDING
        producer.send.assert_not_called()
        producer.close.assert_called_once()

    def test_invalid_batch_size_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="batch_size",
        ):
            OutboxPublisher.publish_pending_events(
                batch_size=0,
            )
