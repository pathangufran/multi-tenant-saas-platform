import uuid
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from apps.outbox.models import OutboxEvent
from apps.outbox.services import OutboxService

class OutboxServiceTests(TestCase):

    def test_record_event_creates_pending_event(self):
        with transaction.atomic():
            event = OutboxService.record_event(
                event_type="user.registered",
                aggregate_type="user",
                aggregate_id=str(uuid.uuid4()),
                aggregate_version=1,
                data={
                    "user_id": str(uuid.uuid4()),
                    "email": "test@example.com",
                },
            )

        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )

        self.assertEqual(
            event.producer,
            "auth-service",
        )

        self.assertEqual(
            event.event_type,
            "user.registered",
        )

    def test_record_event_rejects_invalid_event_type(self):
        with transaction.atomic():
            with self.assertRaises(ValueError):
                OutboxService.record_event(
                    event_type="invalid",
                    aggregate_type="user",
                    aggregate_id="123",
                    aggregate_version=1,
                    data={},
                )

    def test_record_event_rejects_invalid_data(self):
        with transaction.atomic():
            with self.assertRaises(ValueError):
                OutboxService.record_event(
                    event_type="user.registered",
                    aggregate_type="user",
                    aggregate_id="123",
                    aggregate_version=1,
                    data="invalid",
                )

    def test_record_event_rejects_invalid_aggregate_version(self):
        with transaction.atomic():
            with self.assertRaises(ValueError):
                OutboxService.record_event(
                    event_type="user.registered",
                    aggregate_type="user",
                    aggregate_id="123",
                    aggregate_version=0,
                    data={},
                )

    def test_record_event_accepts_correlation_and_causation_ids(self):
        correlation_id = uuid.uuid4()
        causation_id = uuid.uuid4()

        with transaction.atomic():
            event = OutboxService.record_event(
                event_type="user.email_verified",
                aggregate_type="user",
                aggregate_id="123",
                aggregate_version=2,
                correlation_id=correlation_id,
                causation_id=causation_id,
                data={},
            )

        self.assertEqual(event.correlation_id, correlation_id)
        self.assertEqual(event.causation_id, causation_id)

class OutboxTransactionBoundaryTests(TransactionTestCase):

    def test_event_requires_active_transaction(self):
        with self.assertRaises(RuntimeError):
            OutboxService.record_event(
                event_type="user.registered",
                aggregate_type="user",
                aggregate_id="123",
                aggregate_version=1,
                data={},
            )

    def test_outbox_event_rolls_back_with_transaction(self):
        event_id = None

        try:
            with transaction.atomic():
                event = OutboxService.record_event(
                    event_type="user.registered",
                    aggregate_type="user",
                    aggregate_id="123",
                    aggregate_version=1,
                    data={},
                )

                event_id = event.event_id

                raise RuntimeError("Simulated transaction failure")

        except RuntimeError:
            pass

        self.assertFalse(
            OutboxEvent.objects.filter(
                event_id=event_id,
            ).exists()
        )