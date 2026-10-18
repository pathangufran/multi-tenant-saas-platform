import uuid
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.invoices.models import Invoice, InvoiceLineItem
from apps.invoices.serializers import (
    InvoiceGenerateSerializer,
    InvoiceListQuerySerializer,
    InvoiceResponseSerializer,
)
from apps.invoices.services import InvoiceService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService

class InvoiceTestBase(TestCase):
    """Shared setup and helpers for class-based invoice tests."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()
        self.plan = self.create_plan()
        self.subscription = self.create_subscription(self.tenant_id)
        self.admin_client = self.create_admin_client()

    def create_plan(self, **overrides):
        data = {
            "code": "PRO",
            "name": "Professional",
            "description": "Professional plan",
            "price": Decimal("999.00"),
            "currency": "INR",
            "billing_interval": Plan.BillingInterval.MONTHLY,
            "is_active": True,
            "is_public": True,
        }
        data.update(overrides)
        return Plan.objects.create(**data)

    def create_subscription(self, tenant_id=None, plan=None):
        subscription = SubscriptionService.create_subscription(
            data={
                "tenant_id": tenant_id or self.tenant_id,
                "plan_id": (plan or self.plan).id,
            }
        )
        # Invoice generation permits ACTIVE and PAST_DUE subscriptions.
        Subscription.objects.filter(id=subscription.id).update(
            status=Subscription.Status.ACTIVE
        )
        subscription.refresh_from_db()
        return subscription

    def create_admin_client(self):
        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        identity = (
            "invoice-admin@example.com"
            if username_field == "email"
            else "invoice-admin"
        )
        user = user_model.objects.create_superuser(
            **{username_field: identity},
            password="test-password",
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def generate_invoice(self, **overrides):
        data = {
            "subscription_id": self.subscription.id,
            "tax_amount": Decimal("0.00"),
            "due_days": 7,
        }
        data.update(overrides)
        return InvoiceService.generate_invoice(**data)

    def create_invoice(self, **overrides):
        now = timezone.now()
        data = {
            "invoice_number": f"INV-TEST-{uuid.uuid4().hex[:12].upper()}",
            "tenant_id": self.subscription.tenant_id,
            "subscription": self.subscription,
            "plan_code": self.plan.code,
            "plan_name": self.plan.name,
            "currency": self.plan.currency,
            "billing_interval": self.plan.billing_interval,
            "period_start": self.subscription.current_period_start,
            "period_end": self.subscription.current_period_end,
            "subtotal": Decimal("999.00"),
            "tax_amount": Decimal("0.00"),
            "total": Decimal("999.00"),
            "status": Invoice.Status.OPEN,
            "issued_at": now,
            "due_at": now + timedelta(days=7),
        }
        data.update(overrides)
        return Invoice.objects.create(**data)


class InvoiceGenerationServiceTests(InvoiceTestBase):
    def test_generates_invoice_with_uuid_number_and_open_status(self):
        invoice = self.generate_invoice()
        self.assertIsNotNone(invoice.id)
        self.assertTrue(invoice.invoice_number.startswith("INV-"))
        self.assertEqual(invoice.tenant_id, self.subscription.tenant_id)
        self.assertEqual(invoice.subscription_id, self.subscription.id)
        self.assertEqual(invoice.status, Invoice.Status.OPEN)

    def test_invoice_captures_plan_snapshot(self):
        invoice = self.generate_invoice()
        self.assertEqual(invoice.plan_code, self.plan.code)
        self.assertEqual(invoice.plan_name, self.plan.name)
        self.assertEqual(invoice.currency, self.plan.currency)
        self.assertEqual(invoice.billing_interval, self.plan.billing_interval)
        self.assertEqual(invoice.subtotal, Decimal("999.00"))
        self.assertEqual(invoice.tax_amount, Decimal("0.00"))
        self.assertEqual(invoice.total, Decimal("999.00"))

    def test_tax_is_included_in_total(self):
        invoice = self.generate_invoice(tax_amount=Decimal("179.82"))
        self.assertEqual(invoice.subtotal, Decimal("999.00"))
        self.assertEqual(invoice.tax_amount, Decimal("179.82"))
        self.assertEqual(invoice.total, Decimal("1178.82"))

    def test_invoice_has_one_line_item(self):
        invoice = self.generate_invoice()
        self.assertEqual(invoice.line_items.count(), 1)
        item = invoice.line_items.get()
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.unit_price, Decimal("999.00"))
        self.assertEqual(item.amount, Decimal("999.00"))
        self.assertIn("professional", item.description.lower())

    def test_invoice_period_matches_subscription(self):
        invoice = self.generate_invoice()
        self.assertEqual(invoice.period_start, self.subscription.current_period_start)
        self.assertEqual(invoice.period_end, self.subscription.current_period_end)

    def test_due_date_uses_due_days(self):
        before = timezone.now()
        invoice = self.generate_invoice(due_days=10)
        self.assertGreaterEqual(invoice.issued_at, before)
        self.assertEqual(invoice.due_at - invoice.issued_at, timedelta(days=10))

    def test_due_date_can_equal_issue_date(self):
        invoice = self.generate_invoice(due_days=0)
        self.assertEqual(invoice.due_at, invoice.issued_at)

    def test_duplicate_period_is_rejected(self):
        self.generate_invoice()
        with self.assertRaises(ValueError):
            self.generate_invoice()

    def test_unknown_subscription_is_rejected(self):
        with self.assertRaises(ValueError):
            InvoiceService.generate_invoice(subscription_id=uuid.uuid4())

    def test_canceled_subscription_is_rejected(self):
        Subscription.objects.filter(id=self.subscription.id).update(
            status=Subscription.Status.CANCELED
        )
        with self.assertRaises(ValueError):
            self.generate_invoice()

    def test_past_due_subscription_is_allowed(self):
        Subscription.objects.filter(id=self.subscription.id).update(
            status=Subscription.Status.PAST_DUE
        )
        invoice = self.generate_invoice()
        self.assertEqual(invoice.status, Invoice.Status.OPEN)

    def test_negative_tax_is_rejected(self):
        with self.assertRaises(ValueError):
            self.generate_invoice(tax_amount=Decimal("-1.00"))

    def test_due_days_above_maximum_are_rejected(self):
        with self.assertRaises(ValueError):
            self.generate_invoice(due_days=366)

    def test_negative_due_days_are_rejected(self):
        with self.assertRaises(ValueError):
            self.generate_invoice(due_days=-1)

    def test_invoice_price_is_a_snapshot(self):
        invoice = self.generate_invoice()
        self.plan.price = Decimal("1499.00")
        self.plan.save(update_fields=["price", "updated_at"])
        invoice.refresh_from_db()
        self.assertEqual(invoice.subtotal, Decimal("999.00"))
        self.assertEqual(invoice.total, Decimal("999.00"))


class InvoiceQueryServiceTests(InvoiceTestBase):
    def test_get_invoice_by_id(self):
        invoice = self.create_invoice()
        result = InvoiceService.get_invoice(invoice_id=invoice.id)
        self.assertEqual(result.id, invoice.id)

    def test_unknown_invoice_by_id_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Invoice not found"):
            InvoiceService.get_invoice(invoice_id=uuid.uuid4())

    def test_get_invoice_by_number(self):
        invoice = self.create_invoice()
        result = InvoiceService.get_invoice_by_number(
            invoice_number=invoice.invoice_number
        )
        self.assertEqual(result.id, invoice.id)

    def test_unknown_invoice_number_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Invoice not found"):
            InvoiceService.get_invoice_by_number(invoice_number="INV-UNKNOWN")

    def test_list_invoices_returns_all(self):
        self.create_invoice()
        other_tenant = uuid.uuid4()
        other_subscription = self.create_subscription(tenant_id=other_tenant)
        self.create_invoice(
            tenant_id=other_tenant,
            subscription=other_subscription,
            period_start=other_subscription.current_period_start,
            period_end=other_subscription.current_period_end,
        )
        self.assertEqual(InvoiceService.list_invoices().count(), 2)

    def test_list_invoices_filters_by_tenant(self):
        invoice = self.create_invoice()
        self.create_invoice(
            tenant_id=uuid.uuid4(),
            subscription=self.create_subscription(tenant_id=uuid.uuid4()),
            period_start=self.subscription.current_period_start + timedelta(days=40),
            period_end=self.subscription.current_period_end + timedelta(days=40),
        )
        results = InvoiceService.list_invoices(tenant_id=self.tenant_id)
        self.assertEqual(list(results.values_list("id", flat=True)), [invoice.id])

    def test_list_invoices_filters_by_status(self):
        open_invoice = self.create_invoice()
        self.create_invoice(
            period_start=self.subscription.current_period_start + timedelta(days=40),
            period_end=self.subscription.current_period_end + timedelta(days=40),
            status=Invoice.Status.VOID,
        )
        results = InvoiceService.list_invoices(status=Invoice.Status.OPEN)
        self.assertEqual(list(results.values_list("id", flat=True)), [open_invoice.id])


class InvoiceVoidServiceTests(InvoiceTestBase):
    def test_void_invoice_sets_status_and_timestamp(self):
        invoice = self.create_invoice()
        result = InvoiceService.void_invoice(invoice_id=invoice.id)
        self.assertEqual(result.status, Invoice.Status.VOID)
        self.assertIsNotNone(result.voided_at)

    def test_voiding_invoice_twice_is_idempotent(self):
        invoice = self.create_invoice()
        first = InvoiceService.void_invoice(invoice_id=invoice.id)
        second = InvoiceService.void_invoice(invoice_id=invoice.id)
        self.assertEqual(second.status, Invoice.Status.VOID)
        self.assertEqual(second.voided_at, first.voided_at)

    def test_paid_invoice_cannot_be_voided(self):
        invoice = self.create_invoice(
            status=Invoice.Status.PAID,
            paid_at=timezone.now(),
        )
        with self.assertRaises(ValueError):
            InvoiceService.void_invoice(invoice_id=invoice.id)

    def test_uncollectible_invoice_cannot_be_voided(self):
        invoice = self.create_invoice(status=Invoice.Status.UNCOLLECTIBLE)
        with self.assertRaises(ValueError):
            InvoiceService.void_invoice(invoice_id=invoice.id)

    def test_unknown_invoice_cannot_be_voided(self):
        with self.assertRaisesRegex(ValueError, "Invoice not found"):
            InvoiceService.void_invoice(invoice_id=uuid.uuid4())


class InvoiceSerializerTests(InvoiceTestBase):
    def test_generate_serializer_accepts_valid_data(self):
        serializer = InvoiceGenerateSerializer(
            data={
                "subscription_id": str(self.subscription.id),
                "tax_amount": "180.00",
                "due_days": 7,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["tax_amount"], Decimal("180.00"))
        self.assertEqual(serializer.validated_data["due_days"], 7)

    def test_generate_serializer_rejects_negative_tax(self):
        serializer = InvoiceGenerateSerializer(
            data={
                "subscription_id": str(self.subscription.id),
                "tax_amount": "-1.00",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("tax_amount", serializer.errors)

    def test_generate_serializer_rejects_invalid_subscription_id(self):
        serializer = InvoiceGenerateSerializer(data={"subscription_id": "not-a-uuid"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("subscription_id", serializer.errors)

    def test_generate_serializer_rejects_due_days_out_of_range(self):
        serializer = InvoiceGenerateSerializer(
            data={"subscription_id": str(self.subscription.id), "due_days": 366}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("due_days", serializer.errors)

    def test_list_serializer_rejects_invalid_tenant_id(self):
        serializer = InvoiceListQuerySerializer(data={"tenant_id": "not-a-uuid"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("tenant_id", serializer.errors)

    def test_list_serializer_accepts_valid_status(self):
        serializer = InvoiceListQuerySerializer(
            data={
                "tenant_id": str(self.tenant_id),
                "status": Invoice.Status.OPEN,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["status"], Invoice.Status.OPEN)

    def test_response_serializer_includes_line_items_and_nullable_dates(self):
        invoice = self.create_invoice()
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Professional subscription (monthly)",
            quantity=1,
            unit_price=Decimal("999.00"),
            amount=Decimal("999.00"),
        )
        serializer = InvoiceResponseSerializer(invoice)
        self.assertEqual(serializer.data["invoice_number"], invoice.invoice_number)
        self.assertEqual(serializer.data["total"], "999.00")
        self.assertEqual(len(serializer.data["line_items"]), 1)
        self.assertIsNone(serializer.data["paid_at"])
        self.assertIsNone(serializer.data["voided_at"])


class InvoiceAdminAPITests(InvoiceTestBase):
    def test_admin_can_generate_invoice(self):
        response = self.admin_client.post(
            "/api/v1/invoices/admin/create/",
            data={
                "subscription_id": str(self.subscription.id),
                "tax_amount": "180.00",
                "due_days": 7,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], Invoice.Status.OPEN)
        self.assertEqual(response.data["total"], "1179.00")

    def test_admin_can_list_invoices(self):
        invoice = self.create_invoice()
        response = self.admin_client.get(
            "/api/v1/invoices/admin/list/",
            {"tenant_id": str(self.tenant_id)},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(invoice.id))

    def test_admin_can_get_invoice_by_id(self):
        invoice = self.create_invoice()
        response = self.admin_client.get(
            f"/api/v1/invoices/admin/{invoice.id}/detail/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["invoice_number"], invoice.invoice_number)

    def test_admin_can_get_invoice_by_number(self):
        invoice = self.create_invoice()
        response = self.admin_client.get(
            f"/api/v1/invoices/admin/{invoice.invoice_number}/number/detail/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(invoice.id))

    def test_admin_can_void_invoice(self):
        invoice = self.create_invoice()
        response = self.admin_client.patch(
            f"/api/v1/invoices/admin/{invoice.id}/void/",
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], Invoice.Status.VOID)

    def test_non_admin_cannot_generate_invoice(self):
        response = APIClient().post(
            "/api/v1/invoices/admin/create/",
            data={"subscription_id": str(self.subscription.id)},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))
