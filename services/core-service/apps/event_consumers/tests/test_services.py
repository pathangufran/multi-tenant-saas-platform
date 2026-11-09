import uuid
from datetime import datetime, timezone
from unittest.mock import Mock
from django.test import TestCase
from apps.event_consumers.exceptions import (
    EventProcessingError,
    InvalidEventError,
)
from apps.event_consumers.models import ProcessedEvent
from apps.event_consumers.registry import event_handler_registry
from apps.event_consumers.services import EventProcessingService

class EventProcessingServiceTests(TestCase):

    def setUp(self):

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

        event_handler_registry.clear()

    def tearDown(self):
        event_handler_registry.clear()

    def test_registered_event_is_processed(self):

        handler = Mock()

        event_handler_registry.register(
            "project.created",
            handler,
        )

        result = EventProcessingService.process_event(
            self.event
        )

        self.assertEqual(
            result["status"],
            "PROCESSED",
        )

        handler.assert_called_once_with(self.event)

        self.assertTrue(
            ProcessedEvent.objects.filter(
                event_id=self.event_id,
                status=ProcessedEvent.Status.PROCESSED,
            ).exists()
        )

    def test_duplicate_event_is_not_processed_twice(self):

        handler = Mock()

        event_handler_registry.register(
            "project.created",
            handler,
        )

        EventProcessingService.process_event(self.event)

        result = EventProcessingService.process_event(
            self.event
        )

        self.assertEqual(
            result["status"],
            "DUPLICATE",
        )

        handler.assert_called_once()

        self.assertEqual(
            ProcessedEvent.objects.filter(
                event_id=self.event_id
            ).count(),
            1,
        )

    def test_unregistered_event_is_ignored(self):

        result = EventProcessingService.process_event(
            self.event
        )

        self.assertEqual(
            result["status"],
            "IGNORED",
        )

        record = ProcessedEvent.objects.get(
            event_id=self.event_id
        )

        self.assertEqual(
            record.status,
            ProcessedEvent.Status.IGNORED,
        )

    def test_handler_failure_rolls_back_processed_record(self):

        def failing_handler(event):
            raise RuntimeError("Database operation failed")

        event_handler_registry.register(
            "project.created",
            failing_handler,
        )

        with self.assertRaises(EventProcessingError):
            EventProcessingService.process_event(
                self.event
            )

        self.assertFalse(
            ProcessedEvent.objects.filter(
                event_id=self.event_id
            ).exists()
        )

    def test_invalid_event_is_rejected(self):

        event = self.event.copy()
        event["event_id"] = "invalid-uuid"

        with self.assertRaises(InvalidEventError):
            EventProcessingService.process_event(event)

        self.assertEqual(
            ProcessedEvent.objects.count(),
            0,
        )

    def test_handler_receives_complete_event(self):

        received_events = []

        def handler(event):
            received_events.append(event)

        event_handler_registry.register(
            "project.created",
            handler,
        )

        EventProcessingService.process_event(
            self.event
        )

        self.assertEqual(
            received_events,
            [self.event],
        )

    def test_ignored_event_is_not_processed_again(self):

        first_result = EventProcessingService.process_event(
            self.event
        )

        second_result = EventProcessingService.process_event(
            self.event
        )

        self.assertEqual(
            first_result["status"],
            "IGNORED",
        )

        self.assertEqual(
            second_result["status"],
            "DUPLICATE",
        )