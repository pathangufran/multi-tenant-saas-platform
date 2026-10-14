import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from apps.invoices.models import Invoice
from apps.invoices.services import InvoiceService
from apps.payments.models import Payment
from apps.payments.providers import PaymentProviderError
from apps.payments.serializers import PaymentCreateSerializer
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription

User = get_user_model()

class PaymentServiceTests(TestCase):
    def setUp(self):
        self.tenant_id = uuid.uuid4()

        self.plan = Plan.objects.create(
            code="PAYMENT_TEST",
            name="Payment Test Plan",
            description="Plan for payment tests",
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

    def create_second_invoice(self):
        now = timezone.now()
        subscription = Subscription.objects.create(
            tenant_id=uuid.uuid4(),
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            start_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )

        return InvoiceService.generate_invoice(
            subscription_id=subscription.id,
            tax_amount=Decimal("0.00"),
            due_days=7,
        )

    def create_payment(self, **overrides):
        values = {
            "invoice_id": self.invoice.id,
            "idempotency_key": "payment-request-001",
            "provider": Payment.Provider.MOCK,
        }
        values.update(overrides)
        return PaymentService.create_payment(**values)

    def test_create_payment_creates_pending_attempt(self):
        payment = self.create_payment()

        self.assertEqual(payment.invoice_id, self.invoice.id)
        self.assertEqual(payment.amount, Decimal("1179.00"))
        self.assertEqual(payment.currency, "INR")
        self.assertEqual(payment.provider, Payment.Provider.MOCK)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertTrue(payment.provider_payment_id.startswith("mock_"))
        self.assertTrue(payment.checkout_url)
        self.assertEqual(Payment.objects.count(), 1)

    def test_same_idempotency_key_returns_existing_payment(self):
        first = self.create_payment()
        second = self.create_payment()

        self.assertEqual(first.id, second.id)
        self.assertEqual(Payment.objects.count(), 1)

    def test_idempotent_retry_does_not_call_provider_twice(self):
        with patch(
            "apps.payments.services.get_payment_provider"
        ) as provider_factory:
            provider = provider_factory.return_value
            provider.create_payment.return_value = {
                "provider_payment_id": "provider-test-001",
                "checkout_url": (
                    "https://payments.example.invalid/checkout/test"
                ),
                "status": "PENDING",
            }

            first = self.create_payment()
            second = self.create_payment()

        self.assertEqual(first.id, second.id)
        provider.create_payment.assert_called_once()

    def test_key_cannot_be_reused_for_another_invoice(self):
        second_invoice = self.create_second_invoice()

        self.create_payment()

        with self.assertRaises(Exception):
            self.create_payment(
                invoice_id=second_invoice.id,
            )

        self.assertEqual(Payment.objects.count(), 1)

    def test_key_cannot_be_reused_with_another_provider(self):
        self.create_payment()

        with self.assertRaises(Exception):
            self.create_payment(
                provider="ANOTHER_PROVIDER",
            )

        self.assertEqual(Payment.objects.count(), 1)

    def test_missing_invoice_is_rejected(self):
        with self.assertRaises(Exception):
            self.create_payment(invoice_id=uuid.uuid4())

        self.assertEqual(Payment.objects.count(), 0)

    def test_non_open_invoice_is_rejected(self):
        self.invoice.status = Invoice.Status.VOID
        self.invoice.save(update_fields=["status"])

        with self.assertRaises(Exception):
            self.create_payment()

        self.assertEqual(Payment.objects.count(), 0)

    def test_zero_total_invoice_is_rejected(self):
        self.invoice.total = Decimal("0.00")
        self.invoice.save(update_fields=["total"])

        with self.assertRaises(Exception):
            self.create_payment()

        self.assertEqual(Payment.objects.count(), 0)

    def test_payment_amount_is_a_snapshot(self):
        payment = self.create_payment()

        self.invoice.total = Decimal("2500.00")
        self.invoice.save(update_fields=["total"])

        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal("1179.00"))

    def test_provider_error_persists_failed_attempt(self):
        with patch(
            "apps.payments.services.get_payment_provider",
            side_effect=PaymentProviderError("Provider unavailable"),
        ):
            payment = self.create_payment()

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertIn("Provider unavailable", payment.failure_reason)
        self.assertIsNotNone(payment.completed_at)
        self.assertEqual(Payment.objects.count(), 1)

    def test_unsupported_provider_status_fails_attempt(self):
        with patch(
            "apps.payments.services.get_payment_provider"
        ) as provider_factory:
            provider_factory.return_value.create_payment.return_value = {
                "provider_payment_id": "unexpected-001",
                "checkout_url": "",
                "status": "SUCCEEDED",
            }

            payment = self.create_payment()

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertIn("unsupported initial status", payment.failure_reason)

    def test_get_payment_returns_payment(self):
        payment = self.create_payment()

        fetched = PaymentService.get_payment(payment.id)

        self.assertEqual(fetched.id, payment.id)

    def test_get_unknown_payment_raises_not_found(self):
        with self.assertRaises(Exception):
            PaymentService.get_payment(uuid.uuid4())

    def test_list_payments_filters_by_invoice(self):
        payment = self.create_payment()

        results = PaymentService.list_payments(
            invoice_id=self.invoice.id
        )

        self.assertEqual(list(results), [payment])

    def test_list_payments_filters_by_tenant(self):
        payment = self.create_payment()

        results = PaymentService.list_payments(
            tenant_id=self.tenant_id
        )

        self.assertEqual(list(results), [payment])

    def test_list_payments_filters_by_status(self):
        self.create_payment()

        results = PaymentService.list_payments(
            status=Payment.Status.PENDING
        )

        self.assertEqual(results.count(), 1)

        failed_results = PaymentService.list_payments(
            status=Payment.Status.FAILED
        )
        self.assertEqual(failed_results.count(), 0)


class PaymentSerializerTests(TestCase):
    def test_valid_payment_request(self):
        serializer = PaymentCreateSerializer(
            data={
                "invoice_id": str(uuid.uuid4()),
                "idempotency_key": "checkout-001",
                "provider": Payment.Provider.MOCK,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_blank_idempotency_key_is_rejected(self):
        serializer = PaymentCreateSerializer(
            data={
                "invoice_id": str(uuid.uuid4()),
                "idempotency_key": "   ",
                "provider": Payment.Provider.MOCK,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("idempotency_key", serializer.errors)

    def test_invalid_provider_is_rejected(self):
        serializer = PaymentCreateSerializer(
            data={
                "invoice_id": str(uuid.uuid4()),
                "idempotency_key": "checkout-002",
                "provider": "UNKNOWN",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("provider", serializer.errors)


class PaymentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="billing_admin",
            email="billing-admin@example.com",
            password="Test-password-123!",
        )
        self.client.force_authenticate(user=self.admin)

        self.tenant_id = uuid.uuid4()
        self.plan = Plan.objects.create(
            code="PAYMENT_API_TEST",
            name="Payment API Test",
            description="Plan for payment API tests",
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

    def test_admin_can_create_payment(self):
        response = self.client.post(
            reverse("admin-payment-list-create"),
            {
                "invoice_id": str(self.invoice.id),
                "idempotency_key": "api-payment-001",
                "provider": Payment.Provider.MOCK,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Payment.Status.PENDING)
        self.assertEqual(response.data["invoice_id"], str(self.invoice.id))

    def test_admin_can_list_payments(self):
        PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="api-payment-002",
            provider=Payment.Provider.MOCK,
        )

        response = self.client.get(
            reverse("admin-payment-list-create")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_admin_can_filter_payments_by_tenant(self):
        PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="api-payment-003",
            provider=Payment.Provider.MOCK,
        )

        response = self.client.get(
            reverse("admin-payment-list-create"),
            {"tenant_id": str(self.tenant_id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_admin_can_retrieve_payment(self):
        payment = PaymentService.create_payment(
            invoice_id=self.invoice.id,
            idempotency_key="api-payment-004",
            provider=Payment.Provider.MOCK,
        )

        response = self.client.get(
            reverse(
                "admin-payment-detail",
                kwargs={"payment_id": payment.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(payment.id))

    def test_non_admin_cannot_create_payment(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("admin-payment-list-create"),
            {
                "invoice_id": str(self.invoice.id),
                "idempotency_key": "api-payment-005",
                "provider": Payment.Provider.MOCK,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Payment.objects.count(), 0)

    def test_invalid_request_is_rejected(self):
        response = self.client.post(
            reverse("admin-payment-list-create"),
            {
                "invoice_id": str(self.invoice.id),
                "idempotency_key": "",
                "provider": Payment.Provider.MOCK,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_unknown_payment_returns_404(self):
        response = self.client.get(
            reverse(
                "admin-payment-detail",
                kwargs={"payment_id": uuid.uuid4()},
            )
        )

        self.assertEqual(response.status_code, 404)