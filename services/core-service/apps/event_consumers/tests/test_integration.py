import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from django.test import TestCase
from apps.event_consumers.consumer import CoreEventConsumer
from apps.event_consumers.models import (
    ProcessedEvent,
    TenantStatusProjection,
)
from apps.event_consumers.registry import event_handler_registry

class TenantEventIntegrationTests(TestCase):

    def setUp(self):

        self.tenant_id = uuid.uuid4()

        self.consumer = CoreEventConsumer(
            consumer=Mock(),
            dlq_publisher=Mock(),
        )

        self.consumer.dlq_publisher.publish.return_value = {
            "status": "PUBLISHED",
            "event_id": str(uuid.uuid4()),
        }

        self.event_id = str(uuid.uuid4())

    def tearDown(self):
        event_handler_registry.clear()

    def build_event(
        self,
        event_type,
        aggregate_version,
        status,
    ):

        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "event_version": 1,
            "occurred_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "producer": "tenant-service",
            "tenant_id": str(self.tenant_id),
            "aggregate_type": "tenant",
            "aggregate_id": str(self.tenant_id),
            "aggregate_version": aggregate_version,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": "",
            "data": {
                "tenant_id": str(self.tenant_id),
                "name": "Acme",
                "slug": "acme",
                "status": status,
            },
        }

    def build_message(self, event):

        from types import SimpleNamespace

        return SimpleNamespace(
            value=event,
            topic="saas.events.v1",
            partition=0,
            offset=100,
        )

    def test_tenant_created_event_updates_projection(self):

        event = self.build_event(
            "tenant.created",
            1,
            "ACTIVE",
        )

        result = self.consumer.handle_message(
            self.build_message(event)
        )

        self.assertEqual(
            result["status"],
            "PROCESSED",
        )

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )

        self.assertEqual(
            projection.aggregate_version,
            1,
        )

    def test_tenant_suspended_event_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
            aggregate_version=1,
        )

        event = self.build_event(
            "tenant.suspended",
            2,
            "SUSPENDED",
        )

        result = self.consumer.handle_message(
            self.build_message(event)
        )

        self.assertEqual(
            result["status"],
            "PROCESSED",
        )

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.SUSPENDED,
        )

        self.assertEqual(
            projection.aggregate_version,
            2,
        )

    def test_duplicate_event_does_not_repeat_handler(self):

        event = self.build_event(
            "tenant.created",
            1,
            "ACTIVE",
        )

        message = self.build_message(event)

        first_result = self.consumer.handle_message(message)
        second_result = self.consumer.handle_message(message)

        self.assertEqual(
            first_result["status"],
            "PROCESSED",
        )

        self.assertEqual(
            second_result["status"],
            "DUPLICATE",
        )

        self.assertEqual(
            ProcessedEvent.objects.filter(
                event_id=event["event_id"]
            ).count(),
            1,
        )

    def test_stale_event_does_not_change_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
            aggregate_version=3,
        )

        event = self.build_event(
            "tenant.suspended",
            2,
            "SUSPENDED",
        )

        self.consumer.handle_message(
            self.build_message(event)
        )

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )

        self.assertEqual(
            projection.aggregate_version,
            3,
        )

    def test_unregistered_event_is_ignored(self):

        event = self.build_event(
            "member.joined",
            1,
            "ACTIVE",
        )

        result = self.consumer.handle_message(
            self.build_message(event)
        )

        self.assertEqual(
            result["status"],
            "IGNORED",
        )

    @patch(
        "apps.event_consumers.consumer.EventProcessingService.process_event"
    )
    def test_failed_processing_does_not_commit_offset(
        self,
        mock_process,
    ):

        from apps.event_consumers.exceptions import (
            EventProcessingError,
        )

        mock_process.side_effect = EventProcessingError(
            "Temporary database failure"
        )

        from apps.event_consumers.consumer import (
            FailedEventService,
        )

        with patch.object(
            FailedEventService,
            "record_failure",
        ) as mock_record:

            mock_record.return_value = Mock()

            self.consumer.dlq_publisher.publish.side_effect = (
                RuntimeError("DLQ unavailable")
            )

            with self.assertRaises(RuntimeError):
                self.consumer.handle_message(
                    self.build_message(
                        self.build_event(
                            "tenant.created",
                            1,
                            "ACTIVE",
                        )
                    )
                )

        self.consumer.consumer.commit.assert_not_called()