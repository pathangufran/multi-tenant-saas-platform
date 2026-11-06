import uuid
from types import SimpleNamespace
from django.test import TestCase
from apps.event_consumers.failure_services import FailedEventService
from apps.event_consumers.models import FailedEvent

class FailedEventServiceTests(TestCase):

    def setUp(self):
        self.event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.assigned",
        }

        self.message = SimpleNamespace(
            topic="saas.events.v1",
            partition=0,
            offset=12,
        )

    def test_record_failure_creates_record(self):
        failed_event = FailedEventService.record_failure(
            message=self.message,
            event=self.event,
            attempts=5,
            error_message="Handler failed",
        )

        self.assertEqual(failed_event.attempts, 5)
        self.assertEqual(
            failed_event.status,
            FailedEvent.Status.PENDING,
        )

    def test_record_failure_is_idempotent_for_source_message(self):
        first = FailedEventService.record_failure(
            message=self.message,
            event=self.event,
            attempts=5,
            error_message="First failure",
        )

        second = FailedEventService.record_failure(
            message=self.message,
            event=self.event,
            attempts=5,
            error_message="Second failure",
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(FailedEvent.objects.count(), 1)

    def test_mark_published_updates_status(self):
        failed_event = FailedEventService.record_failure(
            message=self.message,
            event=self.event,
            attempts=5,
            error_message="Handler failed",
        )

        FailedEventService.mark_published(failed_event)

        failed_event.refresh_from_db()

        self.assertEqual(
            failed_event.status,
            FailedEvent.Status.PUBLISHED,
        )
        self.assertIsNotNone(failed_event.dlq_published_at)