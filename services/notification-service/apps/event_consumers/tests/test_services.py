import uuid
from django.test import TestCase
from apps.event_consumers.models import ProcessedEvent
from apps.event_consumers.registry import event_handler_registry
from apps.event_consumers.services import EventProcessingService

class EventProcessingServiceTests(TestCase):

    def setUp(self):
        self.event_id = str(uuid.uuid4())

        self.event = {
            "event_id": self.event_id,
            "event_type": "task.assigned",
            "event_version": 1,
            "occurred_at": "2026-11-01T10:00:00+00:00",
            "producer": "core-service",
            "tenant_id": str(uuid.uuid4()),
            "aggregate_type": "task",
            "aggregate_id": str(uuid.uuid4()),
            "aggregate_version": 1,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": None,
            "data": {
                "task_id": str(uuid.uuid4()),
            },
        }

        self.registered_event_type = "test.event"

        self.handler_calls = []

        self.handler = self.make_handler()

        event_handler_registry._handlers.pop(
            self.registered_event_type,
            None,
        )

    def tearDown(self):
        event_handler_registry._handlers.pop(
            self.registered_event_type,
            None,
        )

    def make_handler(self):

        def handler(event):
            self.handler_calls.append(event["event_id"])

        return handler

    def register_test_handler(self):
        self.event["event_type"] = self.registered_event_type

        event_handler_registry.register(
            self.registered_event_type,
            self.handler,
        )

    def test_registered_event_is_processed(self):
        self.register_test_handler()

        result = EventProcessingService.process_event(self.event)

        self.assertEqual(result["status"], "PROCESSED")

        self.assertEqual(len(self.handler_calls), 1)

        self.assertTrue(
            ProcessedEvent.objects.filter(
                event_id=self.event_id,
                status=ProcessedEvent.Status.PROCESSED,
            ).exists()
        )

    def test_duplicate_event_is_not_processed_twice(self):
        self.register_test_handler()

        EventProcessingService.process_event(self.event)
        result = EventProcessingService.process_event(self.event)

        self.assertEqual(result["status"], "DUPLICATE")
        self.assertEqual(len(self.handler_calls), 1)

    def test_unregistered_event_is_ignored(self):
        result = EventProcessingService.process_event(self.event)

        self.assertEqual(result["status"], "IGNORED")

        self.assertTrue(
            ProcessedEvent.objects.filter(
                event_id=self.event_id,
                status=ProcessedEvent.Status.IGNORED,
            ).exists()
        )

    def test_handler_failure_rolls_back_inbox_record(self):
        def failing_handler(event):
            raise RuntimeError("Simulated handler failure")

        self.event["event_type"] = self.registered_event_type

        event_handler_registry.register(
            self.registered_event_type,
            failing_handler,
        )

        with self.assertRaises(Exception):
            EventProcessingService.process_event(self.event)

        self.assertFalse(
            ProcessedEvent.objects.filter(
                event_id=self.event_id,
            ).exists()
        )