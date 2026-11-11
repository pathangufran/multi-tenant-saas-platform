import uuid
from datetime import datetime, timezone
from django.test import TestCase
from apps.event_consumers.handlers import TenantLifecycleHandler
from apps.event_consumers.models import TenantStatusProjection

class TenantLifecycleHandlerTests(TestCase):

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def build_event(
        self,
        event_type,
        aggregate_version,
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
            },
        }

    def test_tenant_created_creates_projection(self):

        event = self.build_event("tenant.created", 1)

        projection = TenantLifecycleHandler.handle(event)

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )
        self.assertEqual(projection.aggregate_version, 1)

    def test_tenant_suspended_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
            aggregate_version=1,
        )

        event = self.build_event("tenant.suspended", 2)

        projection = TenantLifecycleHandler.handle(event)

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.SUSPENDED,
        )
        self.assertEqual(projection.aggregate_version, 2)

    def test_tenant_activated_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.SUSPENDED,
            aggregate_version=2,
        )

        event = self.build_event("tenant.activated", 3)

        projection = TenantLifecycleHandler.handle(event)

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )
        self.assertEqual(projection.aggregate_version, 3)

    def test_tenant_deactivated_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
            aggregate_version=3,
        )

        event = self.build_event("tenant.deactivated", 4)

        projection = TenantLifecycleHandler.handle(event)

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.DEACTIVATED,
        )
        self.assertEqual(projection.aggregate_version, 4)

    def test_stale_event_does_not_overwrite_newer_status(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
            aggregate_version=3,
        )

        stale_event = self.build_event(
            "tenant.suspended",
            2,
        )

        projection = TenantLifecycleHandler.handle(
            stale_event
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )
        self.assertEqual(projection.aggregate_version, 3)

    def test_duplicate_version_does_not_update_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.SUSPENDED,
            aggregate_version=2,
        )

        duplicate_event = self.build_event(
            "tenant.activated",
            2,
        )

        projection = TenantLifecycleHandler.handle(
            duplicate_event
        )

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.SUSPENDED,
        )
        self.assertEqual(projection.aggregate_version, 2)

    def test_newer_event_updates_projection(self):

        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.SUSPENDED,
            aggregate_version=2,
        )

        event = self.build_event(
            "tenant.activated",
            5,
        )

        projection = TenantLifecycleHandler.handle(event)

        self.assertEqual(
            projection.status,
            TenantStatusProjection.Status.ACTIVE,
        )
        self.assertEqual(projection.aggregate_version, 5)

    def test_unknown_event_is_rejected(self):

        event = self.build_event(
            "tenant.unknown",
            1,
        )

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_wrong_aggregate_type_is_rejected(self):

        event = self.build_event(
            "tenant.created",
            1,
        )
        event["aggregate_type"] = "project"

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_missing_payload_tenant_id_is_rejected(self):

        event = self.build_event(
            "tenant.created",
            1,
        )
        event["data"].pop("tenant_id")

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_mismatched_tenant_id_is_rejected(self):

        event = self.build_event(
            "tenant.created",
            1,
        )
        event["data"]["tenant_id"] = str(uuid.uuid4())

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_invalid_tenant_id_is_rejected(self):

        event = self.build_event(
            "tenant.created",
            1,
        )
        event["aggregate_id"] = "invalid-uuid"

        with self.assertRaises(ValueError):
            TenantLifecycleHandler.handle(event)

    def test_duplicate_tenant_created_does_not_duplicate_projection(self):

        event = self.build_event(
            "tenant.created",
            1,
        )

        TenantLifecycleHandler.handle(event)
        TenantLifecycleHandler.handle(event)

        self.assertEqual(
            TenantStatusProjection.objects.filter(
                tenant_id=self.tenant_id
            ).count(),
            1,
        )