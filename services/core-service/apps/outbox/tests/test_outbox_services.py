import uuid
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from apps.outbox.models import OutboxEvent
from apps.outbox.services import OutboxService

class OutboxServiceTests(TestCase):

    def test_record_event_creates_pending_event(self):
        event = OutboxService.record_event(
            event_type="task.assigned",
            aggregate_type="task",
            aggregate_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            aggregate_version=2,
            data={
                "task_id": str(uuid.uuid4()),
                "assigned_to": str(uuid.uuid4()),
            },
        )

        self.assertIsInstance(event, OutboxEvent)
        self.assertEqual(
            event.status,
            OutboxEvent.Status.PENDING,
        )
        self.assertEqual(event.event_type, "task.assigned")
        self.assertEqual(event.producer, "core-service")
        self.assertEqual(event.aggregate_version, 2)
        self.assertEqual(event.attempts, 0)

    def test_record_event_generates_event_id(self):
        event = OutboxService.record_event(
            event_type="project.created",
            aggregate_type="project",
            aggregate_id="project-123",
            data={"project_id": "project-123"},
        )

        self.assertIsNotNone(event.event_id)

    def test_record_event_generates_correlation_id(self):
        event = OutboxService.record_event(
            event_type="project.created",
            aggregate_type="project",
            aggregate_id="project-123",
            data={},
        )

        self.assertIsNotNone(event.correlation_id)

    def test_record_event_uses_supplied_correlation_id(self):
        correlation_id = uuid.uuid4()

        event = OutboxService.record_event(
            event_type="project.created",
            aggregate_type="project",
            aggregate_id="project-123",
            correlation_id=correlation_id,
            data={},
        )

        self.assertEqual(
            event.correlation_id,
            correlation_id,
        )

    def test_record_event_accepts_null_tenant(self):
        event = OutboxService.record_event(
            event_type="user.registered",
            aggregate_type="user",
            aggregate_id="user-123",
            data={"user_id": "user-123"},
        )

        self.assertIsNone(event.tenant_id)

    def test_record_event_rejects_invalid_event_type(self):
        with self.assertRaises(ValueError):
            OutboxService.record_event(
                event_type="TASK_ASSIGNED",
                aggregate_type="task",
                aggregate_id="task-123",
                data={},
            )

    def test_record_event_rejects_missing_aggregate_type(self):
        with self.assertRaises(ValueError):
            OutboxService.record_event(
                event_type="task.assigned",
                aggregate_type="",
                aggregate_id="task-123",
                data={},
            )

    def test_record_event_rejects_missing_aggregate_id(self):
        with self.assertRaises(ValueError):
            OutboxService.record_event(
                event_type="task.assigned",
                aggregate_type="task",
                aggregate_id="",
                data={},
            )

    def test_record_event_rejects_non_dictionary_data(self):
        with self.assertRaises(ValueError):
            OutboxService.record_event(
                event_type="task.assigned",
                aggregate_type="task",
                aggregate_id="task-123",
                data="invalid",
            )

    def test_record_event_rejects_invalid_aggregate_version(self):
        with self.assertRaises(ValueError):
            OutboxService.record_event(
                event_type="task.assigned",
                aggregate_type="task",
                aggregate_id="task-123",
                aggregate_version=0,
                data={},
            )

    def test_record_event_rejects_long_traceparent(self):
        with self.assertRaises(ValueError):
            OutboxService.record_event(
                event_type="task.assigned",
                aggregate_type="task",
                aggregate_id="task-123",
                traceparent="x" * 101,
                data={},
            )

    def test_record_event_stores_event_data(self):
        payload = {
            "task_id": "task-123",
            "assigned_to": "user-123",
        }

        event = OutboxService.record_event(
            event_type="task.assigned",
            aggregate_type="task",
            aggregate_id="task-123",
            data=payload,
        )

        self.assertEqual(event.data, payload)

class OutboxTransactionBoundaryTests(TransactionTestCase):

    def test_record_event_requires_atomic_transaction(self):
        with self.assertRaises(RuntimeError):
            OutboxService.record_event(
                event_type="task.assigned",
                aggregate_type="task",
                aggregate_id="task-123",
                data={},
            )

    def test_domain_change_and_event_rollback_together(self):
        event_id = None

        try:
            with transaction.atomic():
                event = OutboxService.record_event(
                    event_type="task.assigned",
                    aggregate_type="task",
                    aggregate_id="task-123",
                    data={"task_id": "task-123"},
                )

                event_id = event.event_id

                raise ValueError("Simulated transaction failure")

        except ValueError:
            pass

        self.assertFalse(
            OutboxEvent.objects.filter(
                event_id=event_id,
            ).exists()
        )
