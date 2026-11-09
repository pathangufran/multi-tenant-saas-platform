import uuid
from django.test import TestCase
from django.utils import timezone
from apps.event_consumers.models import (
    ProcessedEvent,
    FailedEvent,
)

class ProcessedEventModelTests(TestCase):

    def setUp(self):
        self.event_id = uuid.uuid4()

        self.event_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
        }

    def test_create_processed_event(self):

        event = ProcessedEvent.objects.create(
            event_id=self.event_id,
            event_type="project.created",
            event_version=1,
            producer="core-service",
            tenant_id=uuid.uuid4(),
            payload=self.event_data,
        )

        self.assertEqual(event.event_id, self.event_id)
        self.assertEqual(event.event_type, "project.created")
        self.assertEqual(
            event.status,
            ProcessedEvent.Status.PROCESSED,
        )

    def test_processed_event_id_is_unique(self):

        ProcessedEvent.objects.create(
            event_id=self.event_id,
            event_type="project.created",
            event_version=1,
            producer="core-service",
            payload=self.event_data,
        )

        with self.assertRaises(Exception):
            ProcessedEvent.objects.create(
                event_id=self.event_id,
                event_type="project.created",
                event_version=1,
                producer="core-service",
                payload=self.event_data,
            )

    def test_processed_event_defaults(self):

        event = ProcessedEvent.objects.create(
            event_id=self.event_id,
            event_type="task.created",
            event_version=1,
            producer="core-service",
        )

        self.assertEqual(
            event.status,
            ProcessedEvent.Status.PROCESSED,
        )
        self.assertEqual(event.payload, {})
        self.assertIsNotNone(event.processed_at)

class FailedEventModelTests(TestCase):

    def setUp(self):
        self.event_id = uuid.uuid4()

    def test_create_failed_event(self):

        event = FailedEvent.objects.create(
            event_id=self.event_id,
            event_type="project.created",
            topic="saas.events.v1",
            partition=0,
            offset=10,
            attempts=3,
            error_message="Handler execution failed",
            original_payload={"event_id": str(self.event_id)},
        )

        self.assertEqual(event.event_id, self.event_id)
        self.assertEqual(event.attempts, 3)
        self.assertEqual(
            event.status,
            FailedEvent.Status.PENDING,
        )

    def test_failed_event_default_status(self):

        event = FailedEvent.objects.create(
            event_id=self.event_id,
            topic="saas.events.v1",
            partition=0,
            offset=11,
        )

        self.assertEqual(
            event.status,
            FailedEvent.Status.PENDING,
        )
        self.assertEqual(event.attempts, 0)

    def test_failed_event_source_is_unique(self):

        FailedEvent.objects.create(
            event_id=self.event_id,
            topic="saas.events.v1",
            partition=0,
            offset=10,
        )

        with self.assertRaises(Exception):
            FailedEvent.objects.create(
                event_id=self.event_id,
                topic="saas.events.v1",
                partition=0,
                offset=10,
            )

    def test_mark_failed_event_as_published(self):

        event = FailedEvent.objects.create(
            event_id=self.event_id,
            topic="saas.events.v1",
            partition=0,
            offset=10,
        )

        event.status = FailedEvent.Status.PUBLISHED
        event.dlq_published_at = timezone.now()

        event.save(
            update_fields=[
                "status",
                "dlq_published_at",
                "updated_at",
            ]
        )

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            FailedEvent.Status.PUBLISHED,
        )
        self.assertIsNotNone(event.dlq_published_at)