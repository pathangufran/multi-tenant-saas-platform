import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from apps.integrations.clients import (
    RemoteServiceRejected,
    RemoteServiceUnavailable,
    TenantServiceClient,
)
from apps.integrations.models import (
    BillingEvent,
    BillingEventDelivery,
)
from apps.integrations.services import BillingIntegrationService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription

User = get_user_model()

@override_settings(
    TENANT_SERVICE_URL="http://tenant-service:8000",
    CORE_SERVICE_URL="http://core-service:8000",
    NOTIFICATION_SERVICE_URL="http://notification-service:8000",
    INTERNAL_SERVICE_KEY="integration-test-key",
    INTEGRATION_TIMEOUT_SECONDS=2,
)
class TenantServiceClientTests(TestCase):
    @patch("apps.integrations.clients.requests.post")
    def test_active_tenant_is_validated(self, mock_post):
        tenant_id = uuid.uuid4()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": str(tenant_id),
            "status": "ACTIVE",
        }
        mock_post.return_value = mock_response

        result = TenantServiceClient.validate_tenant(tenant_id)

        self.assertEqual(result["id"], str(tenant_id))
        args, kwargs = mock_post.call_args
        self.assertEqual(
            args[0],
            "http://tenant-service:8000/api/internal/v1/tenants/validate/",
        )
        self.assertEqual(
            kwargs["headers"]["X-Internal-Service-Key"],
            "integration-test-key",
        )
        self.assertEqual(kwargs["timeout"], 2)

    @patch("apps.integrations.clients.requests.post")
    def test_inactive_tenant_is_rejected(self, mock_post):
        tenant_id = uuid.uuid4()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": str(tenant_id),
            "status": "SUSPENDED",
        }
        mock_post.return_value = mock_response

        with self.assertRaises(RemoteServiceRejected):
            TenantServiceClient.validate_tenant(tenant_id)

    @patch(
        "apps.integrations.clients.requests.post",
        side_effect=__import__("requests").Timeout(),
    )
    def test_tenant_service_timeout_fails_closed(self, mock_post):
        with self.assertRaises(RemoteServiceUnavailable):
            TenantServiceClient.validate_tenant(uuid.uuid4())

    @patch("apps.integrations.clients.requests.post")
    def test_missing_tenant_is_rejected(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_post.return_value = mock_response

        with self.assertRaises(RemoteServiceRejected):
            TenantServiceClient.validate_tenant(uuid.uuid4())


@override_settings(
    CORE_SERVICE_URL="http://core-service:8000",
    NOTIFICATION_SERVICE_URL="http://notification-service:8000",
    INTERNAL_SERVICE_KEY="integration-test-key",
    INTEGRATION_TIMEOUT_SECONDS=2,
)
class BillingOutboxTests(TestCase):
    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def create_event(self):
        return BillingIntegrationService.create_event(
            event_type="billing.subscription.created",
            aggregate_type="subscription",
            aggregate_id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            payload={
                "tenant_id": str(self.tenant_id),
                "status": "ACTIVE",
            },
        )

    def test_create_event_creates_one_delivery_per_destination(self):
        event = self.create_event()

        self.assertEqual(event.status, BillingEvent.Status.PENDING)
        self.assertEqual(event.deliveries.count(), 2)
        self.assertSetEqual(
            set(event.deliveries.values_list("destination", flat=True)),
            {"CORE", "NOTIFICATION"},
        )

    @patch("apps.integrations.services.requests.post")
    def test_dispatch_delivers_to_all_destinations(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = ""
        mock_post.return_value = mock_response

        event = self.create_event()
        result = BillingIntegrationService.dispatch_event(event.id)

        event.refresh_from_db()

        self.assertEqual(result["status"], BillingEvent.Status.DELIVERED)
        self.assertEqual(event.status, BillingEvent.Status.DELIVERED)
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(
            event.deliveries.filter(
                status=BillingEventDelivery.Status.DELIVERED
            ).count(),
            2,
        )

    @patch("apps.integrations.services.requests.post")
    def test_failed_delivery_is_scheduled_for_retry(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"
        mock_post.return_value = mock_response

        event = self.create_event()
        BillingIntegrationService.dispatch_event(event.id)

        deliveries = event.deliveries.all()

        self.assertEqual(
            deliveries.filter(
                status=BillingEventDelivery.Status.FAILED
            ).count(),
            2,
        )
        for delivery in deliveries:
            self.assertEqual(delivery.attempts, 1)
            self.assertIsNotNone(delivery.next_attempt_at)
            self.assertIn("503", delivery.last_error)

    @patch("apps.integrations.services.requests.post")
    def test_one_failed_destination_does_not_redeliver_successful_destination(
        self,
        mock_post,
    ):
        mock_post.side_effect = [
            Mock(status_code=202, text=""),
            Mock(status_code=503, text="Temporary failure"),
        ]

        event = self.create_event()
        BillingIntegrationService.dispatch_event(event.id)

        mock_post.reset_mock()
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = ""
        mock_post.return_value = mock_response

        event.deliveries.filter(
            destination="NOTIFICATION"
        ).update(next_attempt_at=None)

        BillingIntegrationService.dispatch_event(event.id)

        # Only the previously unsuccessful destination is retried.
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(
            event.deliveries.filter(
                status=BillingEventDelivery.Status.DELIVERED
            ).count(),
            2,
        )

    @patch(
        "apps.integrations.services.requests.post",
        side_effect=__import__("requests").Timeout(),
    )
    def test_network_error_is_recorded(self, mock_post):
        event = self.create_event()

        BillingIntegrationService.dispatch_event(event.id)

        self.assertEqual(
            event.deliveries.filter(
                status=BillingEventDelivery.Status.FAILED
            ).count(),
            2,
        )

    @patch("apps.integrations.services.requests.post")
    def test_retry_event_resets_failed_deliveries(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Failure"
        mock_post.return_value = mock_response

        event = self.create_event()
        BillingIntegrationService.dispatch_event(event.id)

        mock_response.status_code = 202
        mock_response.text = ""

        result = BillingIntegrationService.retry_event(event.id)

        event.refresh_from_db()
        self.assertEqual(result["status"], BillingEvent.Status.DELIVERED)
        self.assertEqual(event.status, BillingEvent.Status.DELIVERED)

    def test_unknown_event_returns_not_found_result(self):
        result = BillingIntegrationService.dispatch_event(uuid.uuid4())

        self.assertEqual(result["status"], "not_found")


@override_settings(
    CORE_SERVICE_URL="http://core-service:8000",
    NOTIFICATION_SERVICE_URL="http://notification-service:8000",
    INTERNAL_SERVICE_KEY="integration-test-key",
    INTEGRATION_TIMEOUT_SECONDS=2,
)
class BillingIntegrationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="integration_admin",
            email="integration-admin@example.com",
            password="Test-password-123!",
        )
        self.client.force_authenticate(user=self.admin)

        self.tenant_id = uuid.uuid4()
        self.event = BillingIntegrationService.create_event(
            event_type="billing.subscription.created",
            aggregate_type="subscription",
            aggregate_id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            payload={"tenant_id": str(self.tenant_id)},
        )

    def test_admin_can_list_events(self):
        response = self.client.get(
            reverse("admin-billing-event-list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_admin_can_filter_events_by_tenant(self):
        response = self.client.get(
            reverse("admin-billing-event-list"),
            {"tenant_id": str(self.tenant_id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_admin_can_retrieve_event_and_deliveries(self):
        response = self.client.get(
            reverse(
                "admin-billing-event-detail",
                kwargs={"event_id": self.event.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["event"]["id"], str(self.event.id))
        self.assertEqual(len(response.data["deliveries"]), 2)

    @patch("apps.integrations.services.requests.post")
    def test_admin_can_retry_event(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = ""
        mock_post.return_value = mock_response

        response = self.client.post(
            reverse(
                "admin-billing-event-retry",
                kwargs={"event_id": self.event.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["event"]["status"],
            BillingEvent.Status.DELIVERED,
        )

    def test_unknown_event_returns_404(self):
        response = self.client.get(
            reverse(
                "admin-billing-event-detail",
                kwargs={"event_id": uuid.uuid4()},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_list_events(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("admin-billing-event-list")
        )

        self.assertIn(response.status_code, (401, 403))