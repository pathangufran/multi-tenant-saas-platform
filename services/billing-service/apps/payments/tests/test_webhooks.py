import json
import uuid
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from apps.invoices.models import Invoice
from apps.invoices.services import InvoiceService
from apps.payments.models import Payment, WebhookEvent
from apps.payments.providers import generate_mock_webhook_signature
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription

User = get_user_model()
TEST_SECRET = "local-test-webhook-secret-123456789"

@override_settings(PAYMENT_WEBHOOK_SECRET=TEST_SECRET)
class PaymentWebhookServiceTests(TestCase):
    def setUp(self):
        self.tenant_id = uuid.uuid4()

        self.plan = Plan.objects.create(
            code="WEBHOOK_TEST",
            name="Webhook Test Plan",
            description="Plan for webhook tests",
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

        self.payment = PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="webhook-test-payment-001",
            provider=Payment.Provider.MOCK,
        )

    def make_payload(
        self,
        *,
        event_id=None,
        event_type="payment.succeeded",
        payment_status=Payment.Status.SUCCEEDED,
    ):
        return {
            "id": event_id or f"evt_{uuid.uuid4().hex}",
            "type": event_type,
            "data": {
                "provider_payment_id": self.payment.provider_payment_id,
                "status": payment_status,
            },
        }

    def process_payload(self, payload):
        from apps.payments.serializers import PaymentWebhookSerializer
        from apps.payments.services import PaymentWebhookService

        serializer = PaymentWebhookSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        return PaymentWebhookService.process_event(
            provider=Payment.Provider.MOCK,
            validated_data=serializer.validated_data,
            payload=payload,
        )

    def test_successful_event_marks_payment_succeeded(self):
        payload = self.make_payload()

        result = self.process_payload(payload)

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCEEDED,
        )
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(self.invoice.paid_at)
        self.assertEqual(
            result["event"].status,
            WebhookEvent.Status.PROCESSED,
        )
        self.assertFalse(result["duplicate"])

    def test_successful_event_is_persisted(self):
        payload = self.make_payload(event_id="evt_persisted_001")

        self.process_payload(payload)

        self.assertTrue(
            WebhookEvent.objects.filter(
                provider=Payment.Provider.MOCK,
                event_id="evt_persisted_001",
                status=WebhookEvent.Status.PROCESSED,
            ).exists()
        )

    def test_duplicate_event_does_not_repeat_processing(self):
        payload = self.make_payload(event_id="evt_duplicate_001")

        first = self.process_payload(payload)
        second = self.process_payload(payload)

        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(
            WebhookEvent.objects.filter(
                provider=Payment.Provider.MOCK,
                event_id="evt_duplicate_001",
            ).count(),
            1,
        )

    def test_same_event_id_with_different_payload_is_rejected(self):
        payload = self.make_payload(event_id="evt_reused_001")
        self.process_payload(payload)

        changed_payload = {
            **payload,
            "type": "payment.failed",
            "data": {
                **payload["data"],
                "status": Payment.Status.FAILED,
            },
        }

        from rest_framework.exceptions import ValidationError
        from apps.payments.serializers import PaymentWebhookSerializer
        from apps.payments.services import PaymentWebhookService

        serializer = PaymentWebhookSerializer(data=changed_payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(ValidationError):
            PaymentWebhookService.process_event(
                provider=Payment.Provider.MOCK,
                validated_data=serializer.validated_data,
                payload=changed_payload,
            )

    def test_failed_payment_event_does_not_pay_invoice(self):
        payload = self.make_payload(
            event_type="payment.failed",
            payment_status=Payment.Status.FAILED,
        )

        self.process_payload(payload)

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.invoice.status, Invoice.Status.OPEN)
        self.assertIsNotNone(self.payment.completed_at)

    def test_canceled_payment_event_does_not_pay_invoice(self):
        payload = self.make_payload(
            event_type="payment.canceled",
            payment_status=Payment.Status.CANCELED,
        )

        self.process_payload(payload)

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.CANCELED)
        self.assertEqual(self.invoice.status, Invoice.Status.OPEN)

    def test_refund_requires_successful_payment(self):
        payload = self.make_payload(
            event_type="payment.refunded",
            payment_status=Payment.Status.REFUNDED,
        )

        result = self.process_payload(payload)

        self.payment.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(result["event"].status, WebhookEvent.Status.FAILED)
        self.assertEqual(result["error"], "invalid_transition")

    def test_successful_payment_can_be_refunded(self):
        success_payload = self.make_payload(
            event_id="evt_before_refund_001",
        )
        self.process_payload(success_payload)

        refund_payload = self.make_payload(
            event_id="evt_refund_001",
            event_type="payment.refunded",
            payment_status=Payment.Status.REFUNDED,
        )
        self.process_payload(refund_payload)

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)
        # Refund processing does not rewrite invoice accounting status.
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_unknown_provider_payment_id_is_recorded_as_failed_event(self):
        payload = self.make_payload(event_id="evt_unknown_payment_001")
        payload["data"]["provider_payment_id"] = "missing-provider-id"

        result = self.process_payload(payload)

        self.assertEqual(result["error"], "payment_not_found")
        self.assertEqual(
            result["event"].status,
            WebhookEvent.Status.FAILED,
        )

    def test_invalid_transition_is_rejected(self):
        failed_payload = self.make_payload(
            event_id="evt_failed_001",
            event_type="payment.failed",
            payment_status=Payment.Status.FAILED,
        )
        self.process_payload(failed_payload)

        succeeded_payload = self.make_payload(
            event_id="evt_late_success_001",
            event_type="payment.succeeded",
            payment_status=Payment.Status.SUCCEEDED,
        )
        result = self.process_payload(succeeded_payload)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(result["error"], "invalid_transition")

    def test_invoice_total_is_not_changed_by_webhook(self):
        original_total = self.invoice.total

        self.process_payload(self.make_payload())

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total, original_total)

@override_settings(PAYMENT_WEBHOOK_SECRET=TEST_SECRET)
class PaymentWebhookAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant_id = uuid.uuid4()

        self.plan = Plan.objects.create(
            code="WEBHOOK_API_TEST",
            name="Webhook API Test Plan",
            description="Plan for webhook API tests",
            price=Decimal("500.00"),
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
            tax_amount=Decimal("0.00"),
            due_days=7,
        )

        self.payment = PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="webhook-api-payment-001",
            provider=Payment.Provider.MOCK,
        )

        self.url = reverse("payment-webhook")

    def make_payload(self, event_id=None):
        return {
            "id": event_id or f"evt_api_{uuid.uuid4().hex}",
            "type": "payment.succeeded",
            "data": {
                "provider_payment_id": self.payment.provider_payment_id,
                "status": Payment.Status.SUCCEEDED,
            },
        }

    def post_signed_payload(self, payload, signature_override=None):
        raw_body = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")

        signature = signature_override
        if signature is None:
            signature = generate_mock_webhook_signature(
                raw_body,
                TEST_SECRET,
            )

        return self.client.generic(
            "POST",
            self.url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_PAYMENT_SIGNATURE=signature,
        )

    def test_valid_signature_processes_webhook(self):
        response = self.post_signed_payload(
            self.make_payload("evt_api_success_001")
        )

        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.invoice.refresh_from_db()

        self.assertEqual(self.payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_duplicate_webhook_is_acknowledged(self):
        payload = self.make_payload("evt_api_duplicate_001")

        first = self.post_signed_payload(payload)
        second = self.post_signed_payload(payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.data["duplicate"])
        self.assertTrue(second.data["duplicate"])

    def test_invalid_signature_is_rejected(self):
        response = self.post_signed_payload(
            self.make_payload(),
            signature_override="invalid-signature",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(WebhookEvent.objects.count(), 0)
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_missing_signature_is_rejected(self):
        response = self.post_signed_payload(
            self.make_payload(),
            signature_override="",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(WebhookEvent.objects.count(), 0)

    def test_unknown_payment_returns_404(self):
        payload = self.make_payload("evt_api_unknown_payment_001")
        payload["data"]["provider_payment_id"] = "unknown-payment"

        response = self.post_signed_payload(payload)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(WebhookEvent.objects.count(), 1)

    def test_invalid_event_payload_returns_400(self):
        payload = {
            "id": "evt_api_invalid_001",
            "type": "payment.succeeded",
            "data": {
                "provider_payment_id": self.payment.provider_payment_id,
                "status": Payment.Status.FAILED,
            },
        }

        response = self.post_signed_payload(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0)

    def test_non_json_body_with_valid_signature_returns_400(self):
        raw_body = b"not-json"
        signature = generate_mock_webhook_signature(
            raw_body,
            TEST_SECRET,
        )

        response = self.client.generic(
            "POST",
            self.url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_PAYMENT_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 400)

    def test_unconfigured_secret_fails_closed(self):
        with override_settings(PAYMENT_WEBHOOK_SECRET=""):
            response = self.post_signed_payload(self.make_payload())

        self.assertEqual(response.status_code, 401)