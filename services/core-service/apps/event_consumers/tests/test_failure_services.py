import uuid
from django.test import TestCase
from apps.event_consumers.models import FailedEvent
from apps.event_consumers.failure_services import FailedEventService

class FailedEventServiceTests(TestCase):

    def setUp(self):

        self.event_id = uuid.uuid4()

        self.payload = {
            "event_id": str(self.event_id),
            "event_type": "project.created",
            "data": {
                "project_id": str(uuid.uuid4()),
            },
        }

    def test_record_failure(self):

        failed_event = FailedEventService.record_failure(
            event_id=self.event_id,
            event_type="project.created",
            topic="saas.events.v1",
            partition=0,
            offset=10,
            attempts=3,
            error_message="Handler execution failed",
            original_payload=self.payload,
        )

        self.assertEqual(
            failed_event.event_id,
            self.event_id,
        )

        self.assertEqual(
            failed_event.attempts,
            3,
        )

        self.assertEqual(
            failed_event.status,
            FailedEvent.Status.PENDING,
        )

    def test_record_failure_is_idempotent(self):

        first = FailedEventService.record_failure(
            event_id=self.event_id,
            event_type="project.created",
            topic="saas.events.v1",
            partition=0,
            offset=10,
            attempts=2,
            error_message="First failure",
            original_payload=self.payload,
        )

        second = FailedEventService.record_failure(
            event_id=self.event_id,
            event_type="project.created",
            topic="saas.events.v1",
            partition=0,
            offset=10,
            attempts=4,
            error_message="Repeated failure",
            original_payload=self.payload,
        )

        self.assertEqual(first.pk, second.pk)

        self.assertEqual(
            FailedEvent.objects.count(),
            1,
        )

        second.refresh_from_db()

        self.assertEqual(second.attempts, 4)
        self.assertEqual(
            second.error_message,
            "Repeated failure",
        )

    def test_mark_failure_as_published(self):

        failed_event = FailedEvent.objects.create(
            event_id=self.event_id,
            topic="saas.events.v1",
            partition=0,
            offset=10,
        )

        updated = FailedEventService.mark_published(
            failed_event
        )

        failed_event.refresh_from_db()

        self.assertEqual(updated, 1)

        self.assertEqual(
            failed_event.status,
            FailedEvent.Status.PUBLISHED,
        )

        self.assertIsNotNone(
            failed_event.dlq_published_at
        )

    def test_mark_dlq_publish_failure(self):

        failed_event = FailedEvent.objects.create(
            event_id=self.event_id,
            topic="saas.events.v1",
            partition=0,
            offset=10,
        )

        updated = FailedEventService.mark_publish_failed(
            failed_event,
            "Kafka broker unavailable",
        )

        failed_event.refresh_from_db()

        self.assertEqual(updated, 1)

        self.assertEqual(
            failed_event.status,
            FailedEvent.Status.FAILED,
        )

        self.assertEqual(
            failed_event.error_message,
            "Kafka broker unavailable",
        )

    def test_mark_published_for_missing_record(self):

        failed_event = FailedEvent(
            id=uuid.uuid4(),
            event_id=self.event_id,
            topic="saas.events.v1",
            partition=0,
            offset=10,
        )

        updated = FailedEventService.mark_published(
            failed_event
        )

        self.assertEqual(updated, 0)