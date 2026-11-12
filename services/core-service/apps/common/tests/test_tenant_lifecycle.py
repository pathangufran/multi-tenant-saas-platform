import uuid
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from apps.common.tenant_lifecycle import (
    TenantLifecycleAccessService,
)
from apps.event_consumers.models import TenantStatusProjection

class TenantLifecycleAccessServiceTests(TestCase):

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_active_tenant_is_allowed(self):
        projection = TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.ACTIVE,
            aggregate_version=1,
        )

        result = (
            TenantLifecycleAccessService.ensure_tenant_active(
                self.tenant_id
            )
        )

        self.assertEqual(result.id, projection.id)

    def test_suspended_tenant_is_denied(self):
        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.SUSPENDED,
            aggregate_version=2,
        )

        with self.assertRaises(PermissionDenied):
            TenantLifecycleAccessService.ensure_tenant_active(
                self.tenant_id
            )

    def test_deactivated_tenant_is_denied(self):
        TenantStatusProjection.objects.create(
            tenant_id=self.tenant_id,
            status=TenantStatusProjection.Status.DEACTIVATED,
            aggregate_version=3,
        )

        with self.assertRaises(PermissionDenied):
            TenantLifecycleAccessService.ensure_tenant_active(
                self.tenant_id
            )

    def test_missing_projection_is_denied(self):
        with self.assertRaises(PermissionDenied):
            TenantLifecycleAccessService.ensure_tenant_active(
                self.tenant_id
            )

    def test_missing_tenant_id_is_denied(self):
        with self.assertRaises(PermissionDenied):
            TenantLifecycleAccessService.ensure_tenant_active(
                None
            )