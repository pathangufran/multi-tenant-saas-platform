import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.invoices.models import Invoice
from apps.invoices.services import InvoiceService
from apps.integrations.models import BillingEvent, BillingEventDelivery
from apps.integrations.services import BillingIntegrationService
from apps.payments.models import Payment, WebhookEvent
from apps.payments.providers import generate_mock_webhook_signature
from apps.payments.serializers import PaymentWebhookSerializer
from apps.payments.services import PaymentService, PaymentWebhookService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription

TEST_SECRET = "billing-lifecycle-test-secret-123456"

@override_settings(
    PAYMENT_WEBHOOK_SECRET=TEST_SECRET,
    CORE_SERVICE_URL="http://core-service:8000",
    NOTIFICATION_SERVICE_URL="http://notification-service:8000",
    INTERNAL_SERVICE_KEY="test-internal-key",
    INTEGRATION_TIMEOUT_SECONDS=2,
)
class BillingLifecycleTests(TestCase):
    def setUp(self):
        self.tenant_id = uuid.uuid4()

        self.plan = Plan.objects.create(
            code="LIFECYCLE_TEST",
            name="Lifecycle Test Plan",
            description="Plan for end-to-end billing tests",
            price=Decimal("999.00"),
            currency="INR",
            billing_interval=Plan.BillingInterval.MONTHLY,
            is_active=True,
            is_public=True,
        )

        now = timezone.now()
        self.subscription = Subscription.objects.create(
            tenant_id=self.tenant_id,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )

        self.invoice = InvoiceService.generate_invoice(
            subscription_id=self.subscription.id,
            tax_amount=Decimal("180.00"),
            due_days=7,
        )

    def test_invoice_payment_and_webhook_lifecycle(self):
        # 1. Invoice is generated with the expected total.
        self.assertEqual(self.invoice.subtotal, Decimal("999.00"))
        self.assertEqual(self.invoice.tax_amount, Decimal("180.00"))
        self.assertEqual(self.invoice.total, Decimal("1179.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.OPEN)

        # 2. Payment initiation creates a pending attempt.
        payment = PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="lifecycle-payment-001",
            provider=Payment.Provider.MOCK,
        )
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.amount, self.invoice.total)

        # 3. Process a webhook using the same validated structure
        # as the HTTP webhook endpoint.
        payload = {
            "id": "evt_lifecycle_success_001",
            "type": "payment.succeeded",
            "data": {
                "provider_payment_id": payment.provider_payment_id,
                "status": Payment.Status.SUCCEEDED,
            },
        }

        serializer = PaymentWebhookSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        result = PaymentWebhookService.process_event(
            provider=Payment.Provider.MOCK,
            validated_data=serializer.validated_data,
            payload=payload,
        )

        payment.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(self.invoice.paid_at)
        self.assertEqual(
            result["event"].status,
            WebhookEvent.Status.PROCESSED,
        )

        # 4. Re-delivery of the same event is idempotent.
        duplicate = PaymentWebhookService.process_event(
            provider=Payment.Provider.MOCK,
            validated_data=serializer.validated_data,
            payload=payload,
        )

        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(WebhookEvent.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_payment_retry_does_not_create_another_attempt(self):
        first = PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="lifecycle-idempotent-001",
            provider=Payment.Provider.MOCK,
        )
        second = PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="lifecycle-idempotent-001",
            provider=Payment.Provider.MOCK,
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(Payment.objects.count(), 1)

    def test_billing_event_is_delivered_to_each_destination(self):
        event = BillingIntegrationService.create_event(
            event_type="billing.subscription.created",
            aggregate_type="subscription",
            aggregate_id=str(self.subscription.id),
            tenant_id=self.tenant_id,
            payload={
                "subscription_id": str(self.subscription.id),
                "tenant_id": str(self.tenant_id),
                "status": self.subscription.status,
            },
        )

        self.assertEqual(event.deliveries.count(), 2)

        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = ""

        with patch(
            "apps.integrations.services.requests.post",
            return_value=mock_response,
        ) as mock_post:
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

        for call in mock_post.call_args_list:
            self.assertIn(
                "X-Internal-Service-Key",
                call.kwargs["headers"],
            )
            self.assertEqual(
                call.kwargs["json"]["event_id"],
                str(event.id),
            )

    def test_failed_delivery_does_not_mark_event_delivered(self):
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        with patch(
            "apps.integrations.services.requests.post",
            return_value=mock_response,
        ):
            result = BillingIntegrationService.dispatch_event(
                BillingIntegrationService.create_event(
                    event_type="billing.subscription.created",
                    aggregate_type="subscription",
                    aggregate_id=str(self.subscription.id),
                    tenant_id=self.tenant_id,
                    payload={"tenant_id": str(self.tenant_id)},
                ).id
            )

        self.assertEqual(result["status"], BillingEvent.Status.FAILED)

    def test_webhook_signature_matches_raw_payload(self):
        payload = {
            "id": "evt_signature_check_001",
            "type": "payment.succeeded",
            "data": {
                "provider_payment_id": "mock_example",
                "status": Payment.Status.SUCCEEDED,
            },
        }

        raw_body = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")

        signature = generate_mock_webhook_signature(
            raw_body,
            TEST_SECRET,
        )

        from apps.payments.providers import (
            verify_payment_webhook_signature,
        )

        self.assertTrue(
            verify_payment_webhook_signature(
                provider_name="MOCK",
                raw_body=raw_body,
                signature=signature,
            )
        )

        self.assertFalse(
            verify_payment_webhook_signature(
                provider_name="MOCK",
                raw_body=raw_body + b" ",
                signature=signature,
            )
        )