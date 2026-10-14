import uuid
import pytest
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from apps.entitlements.models import Feature, PlanFeature
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

@pytest.fixture
def tenant_id():
    return uuid.uuid4()

@pytest.fixture
def plan(db):
    return Plan.objects.create(
        code="PRO",
        name="Professional",
        description="Professional plan",
        price=Decimal("999.00"),
        currency="INR",
        billing_interval=Plan.BillingInterval.MONTHLY,
        is_active=True,
        is_public=True,
    )

@pytest.fixture
def subscription(plan, tenant_id):
    return SubscriptionService.create_subscription(
        validated_data={
            "tenant_id": tenant_id,
            "plan_id": plan.id,
        }
    )

@pytest.fixture
def admin_client(db):
    user_model = get_user_model()
    user = user_model.objects.create_superuser(
        username="invoice-admin",
        email="invoice-admin@example.com",
        password="test-password",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def invoice(subscription):
    return InvoiceService.generate_invoice(
        subscription_id=subscription.id,
        tax_amount=Decimal("180.00"),
        due_days=7,
    )

@pytest.mark.django_db
def test_generate_invoice(subscription):
    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
    )

    assert invoice.id is not None
    assert invoice.invoice_number.startswith("INV-")
    assert invoice.tenant_id == subscription.tenant_id
    assert invoice.subscription_id == subscription.id
    assert invoice.status == Invoice.Status.OPEN

@pytest.mark.django_db
def test_invoice_captures_plan_price_and_currency(subscription):
    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
    )

    assert invoice.plan_code == "PRO"
    assert invoice.plan_name == "Professional"
    assert invoice.currency == "INR"
    assert invoice.subtotal == Decimal("999.00")
    assert invoice.total == Decimal("999.00")

@pytest.mark.django_db
def test_invoice_total_includes_tax(subscription):
    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
        tax_amount=Decimal("179.82"),
    )

    assert invoice.subtotal == Decimal("999.00")
    assert invoice.tax_amount == Decimal("179.82")
    assert invoice.total == Decimal("1178.82")

@pytest.mark.django_db
def test_invoice_has_one_line_item(invoice):
    line_items = invoice.line_items.all()

    assert line_items.count() == 1

    item = line_items.first()
    assert item.quantity == 1
    assert item.unit_price == Decimal("999.00")
    assert item.amount == Decimal("999.00")
    assert "professional" in item.description.lower()

@pytest.mark.django_db
def test_invoice_period_matches_subscription(invoice, subscription):
    assert invoice.period_start == subscription.current_period_start
    assert invoice.period_end == subscription.current_period_end

@pytest.mark.django_db
def test_invoice_due_date_uses_due_days(subscription):
    before = timezone.now()

    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
        due_days=10,
    )

    assert invoice.issued_at >= before
    assert invoice.due_at - invoice.issued_at == timedelta(days=10)

@pytest.mark.django_db
def test_invoice_due_date_can_be_issue_date(subscription):
    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
        due_days=0,
    )

    assert invoice.due_at == invoice.issued_at

@pytest.mark.django_db
def test_invoice_number_is_unique(subscription, plan, tenant_id):
    first = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
    )

    assert Invoice.objects.filter(
        invoice_number=first.invoice_number,
    ).count() == 1

@pytest.mark.django_db
def test_duplicate_invoice_for_same_period_is_rejected(subscription):
    InvoiceService.generate_invoice(subscription_id=subscription.id)

    with pytest.raises(ValidationError):
        InvoiceService.generate_invoice(subscription_id=subscription.id)

@pytest.mark.django_db
def test_unknown_subscription_cannot_generate_invoice():
    with pytest.raises(ValidationError):
        InvoiceService.generate_invoice(
            subscription_id=uuid.uuid4(),
        )

@pytest.mark.django_db
def test_canceled_subscription_cannot_generate_invoice(
    subscription,
):
    SubscriptionService.cancel_subscription(
        subscription_id=subscription.id,
        at_period_end=False,
    )

    with pytest.raises(ValidationError):
        InvoiceService.generate_invoice(
            subscription_id=subscription.id,
        )

@pytest.mark.django_db
def test_past_due_subscription_can_generate_invoice(subscription):
    Subscription.objects.filter(id=subscription.id).update(
        status=Subscription.Status.PAST_DUE,
    )

    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
    )

    assert invoice.status == Invoice.Status.OPEN

@pytest.mark.django_db
def test_negative_tax_is_rejected(subscription):
    with pytest.raises(ValidationError):
        InvoiceService.generate_invoice(
            subscription_id=subscription.id,
            tax_amount=Decimal("-1.00"),
        )

@pytest.mark.django_db
def test_invoice_generation_rejects_due_days_out_of_range(subscription):
    with pytest.raises(ValidationError):
        InvoiceService.generate_invoice(
            subscription_id=subscription.id,
            due_days=366,
        )

@pytest.mark.django_db
def test_invoice_snapshots_price_when_plan_price_changes(
    subscription,
    plan,
):
    invoice = InvoiceService.generate_invoice(
        subscription_id=subscription.id,
    )

    plan.price = Decimal("1499.00")
    plan.save(update_fields=["price", "updated_at"])

    invoice.refresh_from_db()

    assert invoice.subtotal == Decimal("999.00")
    assert invoice.total == Decimal("999.00")

@pytest.mark.django_db
def test_get_invoice_by_id(invoice):
    result = InvoiceService.get_invoice(invoice_id=invoice.id)

    assert result is not None
    assert result.id == invoice.id
    assert result.line_items.count() == 1

@pytest.mark.django_db
def test_get_unknown_invoice_returns_none():
    result = InvoiceService.get_invoice(invoice_id=uuid.uuid4())

    assert result is None

@pytest.mark.django_db
def test_get_invoice_by_number(invoice):
    result = InvoiceService.get_invoice_by_number(
        invoice_number=invoice.invoice_number,
    )

    assert result is not None
    assert result.id == invoice.id

@pytest.mark.django_db
def test_get_unknown_invoice_number_returns_none():
    result = InvoiceService.get_invoice_by_number(
        invoice_number="INV-UNKNOWN",
    )

    assert result is None

@pytest.mark.django_db
def test_list_invoices_returns_all(invoice, subscription):
    second_subscription = SubscriptionService.create_subscription(
        validated_data={
            "tenant_id": uuid.uuid4(),
            "plan_id": subscription.plan_id,
        }
    )

    InvoiceService.generate_invoice(
        subscription_id=second_subscription.id,
    )

    assert InvoiceService.list_invoices().count() == 2

@pytest.mark.django_db
def test_list_invoices_filters_by_tenant(invoice, tenant_id):
    results = InvoiceService.list_invoices(tenant_id=tenant_id)

    assert results.count() == 1
    assert results.first().tenant_id == tenant_id

@pytest.mark.django_db
def test_list_invoices_filters_by_status(invoice):
    results = InvoiceService.list_invoices(status=Invoice.Status.OPEN)

    assert results.count() == 1

@pytest.mark.django_db
def test_void_invoice(invoice):
    result = InvoiceService.void_invoice(invoice_id=invoice.id)

    assert result.status == Invoice.Status.VOID
    assert result.voided_at is not None

@pytest.mark.django_db
def test_void_invoice_is_idempotent(invoice):
    first = InvoiceService.void_invoice(invoice_id=invoice.id)
    original_voided_at = first.voided_at

    second = InvoiceService.void_invoice(invoice_id=invoice.id)

    assert second.status == Invoice.Status.VOID
    assert second.voided_at == original_voided_at

@pytest.mark.django_db
def test_paid_invoice_cannot_be_voided(invoice):
    Invoice.objects.filter(id=invoice.id).update(
        status=Invoice.Status.PAID,
        paid_at=timezone.now(),
    )

    with pytest.raises(ValidationError):
        InvoiceService.void_invoice(invoice_id=invoice.id)

@pytest.mark.django_db
def test_uncollectible_invoice_cannot_be_voided(invoice):
    Invoice.objects.filter(id=invoice.id).update(
        status=Invoice.Status.UNCOLLECTIBLE,
    )

    with pytest.raises(ValidationError):
        InvoiceService.void_invoice(invoice_id=invoice.id)

@pytest.mark.django_db
def test_unknown_invoice_cannot_be_voided():
    with pytest.raises(ValidationError):
        InvoiceService.void_invoice(invoice_id=uuid.uuid4())

@pytest.mark.django_db
def test_invoice_generate_serializer_accepts_valid_data(subscription):
    serializer = InvoiceGenerateSerializer(
        data={
            "subscription_id": str(subscription.id),
            "tax_amount": "180.00",
            "due_days": 7,
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["tax_amount"] == Decimal("180.00")

@pytest.mark.django_db
def test_invoice_generate_serializer_rejects_negative_tax(subscription):
    serializer = InvoiceGenerateSerializer(
        data={
            "subscription_id": str(subscription.id),
            "tax_amount": "-1.00",
        }
    )

    assert not serializer.is_valid()
    assert "tax_amount" in serializer.errors

@pytest.mark.django_db
def test_invoice_generate_serializer_rejects_invalid_subscription_id():
    serializer = InvoiceGenerateSerializer(
        data={"subscription_id": "invalid"},
    )

    assert not serializer.is_valid()
    assert "subscription_id" in serializer.errors

@pytest.mark.django_db
def test_invoice_query_serializer_rejects_invalid_tenant_id():
    serializer = InvoiceListQuerySerializer(
        data={"tenant_id": "invalid"},
    )

    assert not serializer.is_valid()
    assert "tenant_id" in serializer.errors

@pytest.mark.django_db
def test_invoice_serializer_includes_line_items(invoice):
    serializer = InvoiceResponseSerializer(invoice)

    assert serializer.data["invoice_number"] == invoice.invoice_number
    assert serializer.data["total"] == "1179.00"
    assert len(serializer.data["line_items"]) == 1

@pytest.mark.django_db
def test_admin_can_generate_invoice(admin_client, subscription):
    response = admin_client.post(
        "/api/v1/invoices/admin/create/",
        data={
            "subscription_id": str(subscription.id),
            "tax_amount": "180.00",
            "due_days": 7,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == Invoice.Status.OPEN
    assert response.data["total"] == "1179.00"

@pytest.mark.django_db
def test_admin_can_list_invoices(admin_client, invoice, tenant_id):
    response = admin_client.get(
        "/api/v1/invoices/admin/list/",
        {"tenant_id": str(tenant_id)},
    )

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(invoice.id)

@pytest.mark.django_db
def test_admin_can_get_invoice(admin_client, invoice):
    response = admin_client.get(
        f"/api/v1/invoices/admin/{invoice.id}/detail/",
    )

    assert response.status_code == 200
    assert response.data["invoice_number"] == invoice.invoice_number

@pytest.mark.django_db
def test_admin_can_get_invoice_by_number(admin_client, invoice):
    response = admin_client.get(
        f"/api/v1/invoices/admin/{invoice.invoice_number}/number/",
    )

    assert response.status_code == 200
    assert response.data["id"] == str(invoice.id)

@pytest.mark.django_db
def test_admin_can_void_invoice(admin_client, invoice):
    response = admin_client.post(
        f"/api/v1/invoices/admin/{invoice.id}/void/",
        data={},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == Invoice.Status.VOID

@pytest.mark.django_db
def test_non_admin_cannot_generate_invoice(subscription):
    response = APIClient().post(
        "/api/v1/invoices/admin/create/",
        data={"subscription_id": str(subscription.id)},
        format="json",
    )

    assert response.status_code in (401, 403)