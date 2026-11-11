import uuid
from datetime import datetime, timezone
from django.test import TestCase
from apps.event_consumers.handlers import TenantLifecycleHandler
from apps.event_consumers.models import TenantStatusProjection

class TenantLifecycleHandlerTests(TestCase):

    def setUp(self):

        self.tenant_id = uuid.uuid4()

    def build_event(self, event_type):

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
            "aggregate_version": 1,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": "",
            "data": {
                "tenant_id": str(self.tenant_id),
                "name": "Acme",
                "slug": "acme",
            },
        }

    def test_tenant_created_creates_active_projection(self):

        event = self.build_event("tenant.created")

        TenantLifecycleHandler.handle(event)

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )

    def test_tenant_suspended_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
        )

        event = self.build_event("tenant.suspended")

        TenantLifecycleHandler.handle(event)

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.SUSPENDED,
        )

    def test_tenant_activated_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.SUSPENDED,
        )

        event = self.build_event("tenant.activated")

        TenantLifecycleHandler.handle(event)

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )

    def test_tenant_deactivated_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
        )

        event = self.build_event("tenant.deactivated")

        TenantLifecycleHandler.handle(event)

        projection = TenantStatusProjection.objects.get(
            tenant_id=self.tenant_id
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.DEACTIVATED,
        )

    def test_unknown_tenant_event_is_rejected(self):

        event = self.build_event("tenant.unknown")

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_missing_tenant_id_is_rejected(self):

        event = self.build_event("tenant.created")
        event["data"].pop("tenant_id")

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_invalid_tenant_id_is_rejected(self):

        event = self.build_event("tenant.created")
        event["data"]["tenant_id"] = "invalid-uuid"

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_duplicate_tenant_created_does_not_duplicate_projection(self):

        event = self.build_event("tenant.created")

        TenantLifecycleHandler.handle(event)
        TenantLifecycleHandler.handle(event)

        self.assertEqual(
            TenantStatusProjection.objects.filter(
                tenant_id=self.tenant_id
            ).count(),
            1,
        )