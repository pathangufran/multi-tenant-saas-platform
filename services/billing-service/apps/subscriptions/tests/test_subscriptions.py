import uuid
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from rest_framework.test import APIClient
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.serializers import (
    SubscriptionCancelSerializer,
    SubscriptionCreateSerializer,
    SubscriptionPlanSerializer,
    SubscriptionResponseSerializer,
)
from apps.subscriptions.services import (
    OPEN_STATUSES,
    SubscriptionService,
    add_billing_interval,
)

class SubscriptionTestDataMixin:
    """Shared factories for class-based tests."""

    def create_plan(
        self,
        *,
        code="STARTER",
        name="Starter",
        price=Decimal("499.00"),
        interval=Plan.BillingInterval.MONTHLY,
        is_active=True,
        is_public=True,
    ):
        return Plan.objects.create(
            code=code,
            name=name,
            price=price,
            currency="INR",
            billing_interval=interval,
            is_active=is_active,
            is_public=is_public,
        )

    def create_subscription(self, *, plan=None, tenant_id=None, start_at=None, **overrides):
        plan = plan or self.create_plan()
        tenant_id = tenant_id or uuid.uuid4()
        start_at = start_at or timezone.now()
        period_end = add_billing_interval(start_at, plan.billing_interval)
        values = {
            "tenant_id": tenant_id,
            "plan": plan,
            "status": Subscription.Status.ACTIVE,
            "start_at": start_at,
            "current_period_start": start_at,
            "current_period_end": period_end,
        }
        values.update(overrides)
        return Subscription.objects.create(**values)

    def subscription_input(self, plan, tenant_id, **extra):
        payload = {"tenant_id": tenant_id, "plan_id": plan.id}
        payload.update(extra)
        return payload

class AddBillingIntervalTests(TestCase):
    def test_adds_one_month(self):
        start = datetime(2026, 1, 15, 10, 0, tzinfo=datetime_timezone.utc)
        result = add_billing_interval(start, Plan.BillingInterval.MONTHLY)
        self.assertEqual(result, datetime(2026, 2, 15, 10, 0, tzinfo=datetime_timezone.utc))

    def test_monthly_interval_clamps_end_of_month(self):
        start = datetime(2026, 1, 31, 10, 0, tzinfo=datetime_timezone.utc)
        result = add_billing_interval(start, Plan.BillingInterval.MONTHLY)
        self.assertEqual((result.year, result.month, result.day), (2026, 2, 28))

    def test_adds_one_year(self):
        start = datetime(2026, 3, 10, 10, 0, tzinfo=datetime_timezone.utc)
        result = add_billing_interval(start, Plan.BillingInterval.YEARLY)
        self.assertEqual(result, datetime(2027, 3, 10, 10, 0, tzinfo=datetime_timezone.utc))

    def test_leap_day_clamps_when_adding_year(self):
        start = datetime(2024, 2, 29, 10, 0, tzinfo=datetime_timezone.utc)
        result = add_billing_interval(start, Plan.BillingInterval.YEARLY)
        self.assertEqual((result.year, result.month, result.day), (2025, 2, 28))

    def test_rejects_unsupported_interval(self):
        with self.assertRaisesMessage(ValueError, "Unsupported billing interval."):
            add_billing_interval(timezone.now(), "WEEKLY")

class SubscriptionModelTests(SubscriptionTestDataMixin, TestCase):
    def test_model_uses_uuid_primary_key(self):
        subscription = self.create_subscription()
        self.assertIsInstance(subscription.id, uuid.UUID)

    def test_string_representation_includes_tenant_plan_and_status(self):
        tenant_id = uuid.uuid4()
        subscription = self.create_subscription(tenant_id=tenant_id)
        self.assertEqual(
            str(subscription),
            f"{tenant_id} - STARTER ({Subscription.Status.ACTIVE})",
        )

    def test_period_end_must_be_after_period_start(self):
        plan = self.create_plan()
        start = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subscription.objects.create(
                tenant_id=uuid.uuid4(),
                plan=plan,
                status=Subscription.Status.ACTIVE,
                start_at=start,
                current_period_start=start,
                current_period_end=start,
            )

    def test_only_one_open_subscription_per_tenant(self):
        tenant_id = uuid.uuid4()
        self.create_subscription(tenant_id=tenant_id)
        plan = self.create_plan(code="PRO", name="Pro")
        start = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subscription.objects.create(
                tenant_id=tenant_id,
                plan=plan,
                status=Subscription.Status.PAST_DUE,
                start_at=start,
                current_period_start=start,
                current_period_end=add_billing_interval(start, plan.billing_interval),
            )

    def test_canceled_subscription_does_not_block_new_open_subscription(self):
        tenant_id = uuid.uuid4()
        self.create_subscription(tenant_id=tenant_id, status=Subscription.Status.CANCELED)
        second = self.create_subscription(
            tenant_id=tenant_id,
            plan=self.create_plan(code="PRO", name="Pro"),
        )
        self.assertEqual(second.status, Subscription.Status.ACTIVE)

    def test_external_subscription_id_must_be_unique_when_nonempty(self):
        external_id = "provider-subscription-123"
        self.create_subscription(external_subscription_id=external_id)
        start = timezone.now()
        plan = self.create_plan(code="PRO", name="Pro")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subscription.objects.create(
                tenant_id=uuid.uuid4(),
                plan=plan,
                status=Subscription.Status.ACTIVE,
                start_at=start,
                current_period_start=start,
                current_period_end=add_billing_interval(start, plan.billing_interval),
                external_subscription_id=external_id,
            )

class SubscriptionCreateSerializerTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.plan = self.create_plan()
        self.tenant_id = uuid.uuid4()

    def test_accepts_valid_required_fields(self):
        serializer = SubscriptionCreateSerializer(
            data={"tenant_id": str(self.tenant_id), "plan_id": str(self.plan.id)}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["tenant_id"], self.tenant_id)
        self.assertEqual(serializer.validated_data["plan_id"], self.plan.id)

    def test_accepts_optional_start_at(self):
        start_at = "2026-01-15T10:00:00Z"
        serializer = SubscriptionCreateSerializer(
            data={
                "tenant_id": str(self.tenant_id),
                "plan_id": str(self.plan.id),
                "start_at": start_at,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNotNone(serializer.validated_data["start_at"])

    def test_rejects_invalid_tenant_uuid(self):
        serializer = SubscriptionCreateSerializer(
            data={"tenant_id": "not-a-uuid", "plan_id": str(self.plan.id)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("tenant_id", serializer.errors)

    def test_rejects_invalid_plan_uuid(self):
        serializer = SubscriptionCreateSerializer(
            data={"tenant_id": str(self.tenant_id), "plan_id": "not-a-uuid"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("plan_id", serializer.errors)

    def test_requires_tenant_and_plan_ids(self):
        serializer = SubscriptionCreateSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("tenant_id", serializer.errors)
        self.assertIn("plan_id", serializer.errors)

class SubscriptionCancelSerializerTests(TestCase):
    def test_uses_declared_default_for_cancel_flag(self):
        serializer = SubscriptionCancelSerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # The uploaded serializer names this field `at_period_at`.
        self.assertTrue(serializer.validated_data["at_period_at"])

    def test_accepts_boolean_cancel_flag(self):
        serializer = SubscriptionCancelSerializer(data={"at_period_at": False})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data["at_period_at"])

class SubscriptionServiceCreateTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.monthly_plan = self.create_plan()
        self.yearly_plan = self.create_plan(
            code="PRO_YEARLY",
            name="Pro Yearly",
            price=Decimal("4999.00"),
            interval=Plan.BillingInterval.YEARLY,
        )
        self.tenant_id = uuid.uuid4()

    def test_creates_subscription_with_expected_fields_and_monthly_period(self):
        start_at = datetime(2026, 1, 15, 10, 0, tzinfo=datetime_timezone.utc)
        subscription = SubscriptionService.create_subscription(
            data=self.subscription_input(self.monthly_plan, self.tenant_id, start_at=start_at)
        )
        self.assertIsNotNone(subscription.id)
        self.assertEqual(subscription.tenant_id, self.tenant_id)
        self.assertEqual(subscription.plan_id, self.monthly_plan.id)
        self.assertEqual(subscription.status, Subscription.Status.ACTIVE)
        self.assertEqual(subscription.current_period_start, start_at)
        self.assertEqual(subscription.current_period_end, datetime(2026, 2, 15, 10, 0, tzinfo=datetime_timezone.utc))

    def test_creates_yearly_billing_period(self):
        start_at = datetime(2026, 3, 10, 10, 0, tzinfo=datetime_timezone.utc)
        subscription = SubscriptionService.create_subscription(
            data=self.subscription_input(self.yearly_plan, self.tenant_id, start_at=start_at)
        )
        self.assertEqual(subscription.current_period_end, datetime(2027, 3, 10, 10, 0, tzinfo=datetime_timezone.utc))

    def test_defaults_start_at_to_current_time(self):
        before = timezone.now()
        subscription = SubscriptionService.create_subscription(
            data=self.subscription_input(self.monthly_plan, self.tenant_id)
        )
        after = timezone.now()
        self.assertGreaterEqual(subscription.start_at, before)
        self.assertLessEqual(subscription.start_at, after)

    def test_rejects_inactive_plan(self):
        inactive_plan = self.create_plan(code="INACTIVE", name="Inactive", is_active=False)
        with self.assertRaises(Plan.DoesNotExist):
            SubscriptionService.create_subscription(
                data=self.subscription_input(inactive_plan, self.tenant_id)
            )

    def test_rejects_unknown_plan(self):
        with self.assertRaises(Plan.DoesNotExist):
            SubscriptionService.create_subscription(
                data={"tenant_id": self.tenant_id, "plan_id": uuid.uuid4()}
            )

    def test_rejects_second_open_subscription_for_same_tenant(self):
        SubscriptionService.create_subscription(
            data=self.subscription_input(self.monthly_plan, self.tenant_id)
        )
        with self.assertRaisesMessage(ValueError, "already has an open subscription"):
            SubscriptionService.create_subscription(
                data=self.subscription_input(self.yearly_plan, self.tenant_id)
            )

    def test_allows_new_subscription_after_immediate_cancellation(self):
        first = SubscriptionService.create_subscription(
            data=self.subscription_input(self.monthly_plan, self.tenant_id)
        )
        SubscriptionService.cancel_subscription(subscription_id=first.id, at_period_end=False)
        second = SubscriptionService.create_subscription(
            data=self.subscription_input(self.yearly_plan, self.tenant_id)
        )
        self.assertEqual(second.status, Subscription.Status.ACTIVE)
        self.assertEqual(second.tenant_id, self.tenant_id)

class SubscriptionServiceReadTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.tenant_id = uuid.uuid4()
        self.subscription = self.create_subscription(tenant_id=self.tenant_id)

    def test_list_subscriptions_filters_by_tenant(self):
        other = self.create_subscription(
            tenant_id=uuid.uuid4(),
            plan=self.create_plan(code="OTHER", name="Other"),
        )
        results = SubscriptionService.list_subscriptions(tenant_id=self.tenant_id)
        self.assertEqual(list(results), [self.subscription])
        self.assertNotIn(other, results)

    def test_get_subscription_returns_subscription_and_plan(self):
        result = SubscriptionService.get_subscription(subscription_id=self.subscription.id)
        self.assertEqual(result.id, self.subscription.id)
        self.assertEqual(result.plan_id, self.subscription.plan_id)

    def test_get_subscription_raises_for_unknown_id(self):
        with self.assertRaises(Subscription.DoesNotExist):
            SubscriptionService.get_subscription(subscription_id=uuid.uuid4())

    def test_get_open_subscription_returns_open_subscription(self):
        result = SubscriptionService.get_open_subscription(tenant_id=self.tenant_id)
        self.assertEqual(result.id, self.subscription.id)

    def test_open_subscription_lookup_excludes_canceled_subscription(self):
        SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=False,
        )
        with self.assertRaises(Subscription.DoesNotExist):
            SubscriptionService.get_open_subscription(tenant_id=self.tenant_id)

    def test_open_statuses_include_trialing_active_and_past_due(self):
        self.assertEqual(
            OPEN_STATUSES,
            {
                Subscription.Status.TRIALING,
                Subscription.Status.ACTIVE,
                Subscription.Status.PAST_DUE,
            },
        )

class SubscriptionServiceCancellationTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.subscription = self.create_subscription()

    def test_schedules_cancellation_at_period_end(self):
        result = SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=True,
        )
        self.assertEqual(result.status, Subscription.Status.ACTIVE)
        self.assertTrue(result.cancel_at_period_end)
        self.assertIsNone(result.canceled_at)
        self.assertIsNone(result.ended_at)

    def test_immediately_cancels_subscription(self):
        result = SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=False,
        )
        self.assertEqual(result.status, Subscription.Status.CANCELED)
        self.assertFalse(result.cancel_at_period_end)
        self.assertIsNotNone(result.canceled_at)
        self.assertIsNotNone(result.ended_at)

    def test_cancellation_is_idempotent_for_already_canceled_subscription(self):
        first = SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=False,
        )
        original_canceled_at = first.canceled_at
        second = SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=False,
        )
        self.assertEqual(second.status, Subscription.Status.CANCELED)
        self.assertEqual(second.canceled_at, original_canceled_at)

    def test_unknown_subscription_raises_does_not_exist(self):
        with self.assertRaises(Subscription.DoesNotExist):
            SubscriptionService.cancel_subscription(
                subscription_id=uuid.uuid4(),
                at_period_end=False,
            )

    def test_expired_subscription_is_not_changed_by_cancel(self):
        self.subscription.status = Subscription.Status.EXPIRED
        self.subscription.ended_at = timezone.now()
        self.subscription.save(update_fields=["status", "ended_at"])
        result = SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=False,
        )
        self.assertEqual(result.status, Subscription.Status.EXPIRED)

class SubscriptionServiceRenewalTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.subscription = self.create_subscription()

    def test_renewal_advances_billing_period(self):
        old_period_end = self.subscription.current_period_end
        result = SubscriptionService.renew_subscription(subscription_id=self.subscription.id)
        self.assertEqual(result.status, Subscription.Status.ACTIVE)
        self.assertGreaterEqual(result.current_period_start, old_period_end)
        self.assertGreater(result.current_period_end, result.current_period_start)

    def test_renewal_accepts_past_due_subscription(self):
        self.subscription.status = Subscription.Status.PAST_DUE
        self.subscription.save(update_fields=["status"])
        result = SubscriptionService.renew_subscription(subscription_id=self.subscription.id)
        self.assertEqual(result.status, Subscription.Status.ACTIVE)

    def test_scheduled_cancellation_prevents_renewal(self):
        SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=True,
        )
        with self.assertRaisesMessage(ValueError, "scheduled for cancellation"):
            SubscriptionService.renew_subscription(subscription_id=self.subscription.id)

    def test_canceled_subscription_cannot_be_renewed(self):
        SubscriptionService.cancel_subscription(
            subscription_id=self.subscription.id,
            at_period_end=False,
        )
        with self.assertRaisesMessage(ValueError, "Only active or past-due"):
            SubscriptionService.renew_subscription(subscription_id=self.subscription.id)

    def test_unknown_subscription_raises_does_not_exist(self):
        with self.assertRaises(Subscription.DoesNotExist):
            SubscriptionService.renew_subscription(subscription_id=uuid.uuid4())

class SubscriptionServiceFinalizePeriodTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.subscription = self.create_subscription()

    def expire_current_period(self, *, scheduled_cancel):
        now = timezone.now()
        Subscription.objects.filter(id=self.subscription.id).update(
            current_period_start=now - timedelta(days=40),
            current_period_end=now - timedelta(days=1),
            cancel_at_period_end=scheduled_cancel,
        )

    def test_finalize_before_period_end_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "billing period has not ended"):
            SubscriptionService.finalize_period_end(subscription_id=self.subscription.id)

    def test_finalize_scheduled_cancellation_marks_subscription_canceled(self):
        self.expire_current_period(scheduled_cancel=True)
        result = SubscriptionService.finalize_period_end(subscription_id=self.subscription.id)
        self.assertEqual(result.status, Subscription.Status.CANCELED)
        self.assertIsNotNone(result.canceled_at)
        self.assertIsNotNone(result.ended_at)
        self.assertFalse(result.cancel_at_period_end)

    def test_finalize_uncanceled_subscription_marks_it_expired(self):
        self.expire_current_period(scheduled_cancel=False)
        result = SubscriptionService.finalize_period_end(subscription_id=self.subscription.id)
        self.assertEqual(result.status, Subscription.Status.EXPIRED)
        self.assertIsNotNone(result.ended_at)

    def test_finalize_non_open_subscription_is_left_unchanged(self):
        self.subscription.status = Subscription.Status.CANCELED
        self.subscription.save(update_fields=["status"])
        result = SubscriptionService.finalize_period_end(subscription_id=self.subscription.id)
        self.assertEqual(result.status, Subscription.Status.CANCELED)

    def test_unknown_subscription_raises_does_not_exist(self):
        with self.assertRaises(Subscription.DoesNotExist):
            SubscriptionService.finalize_period_end(subscription_id=uuid.uuid4())

class SubscriptionResponseSerializerTests(SubscriptionTestDataMixin, TestCase):
    def setUp(self):
        self.subscription = self.create_subscription()

    def test_plan_serializer_exposes_plan_code_and_name(self):
        serializer = SubscriptionPlanSerializer(self.subscription)
        # These assertions describe the intended nested plan representation.
        self.assertEqual(serializer.data.get("plan_code"), "STARTER")
        self.assertEqual(serializer.data.get("plan_name"), "Starter")

    def test_response_serializer_exposes_subscription_fields(self):
        serializer = SubscriptionResponseSerializer(self.subscription)
        data = serializer.data
        self.assertEqual(data["id"], str(self.subscription.id))
        self.assertEqual(data["tenant_id"], str(self.subscription.tenant_id))
        self.assertEqual(data["plan_id"], str(self.subscription.plan_id))
        self.assertEqual(data["status"], Subscription.Status.ACTIVE)

class SubscriptionAdminAPITests(SubscriptionTestDataMixin, TestCase):
    """Endpoint tests for the routes exercised by the original test file."""

    list_url = "/api/v1/admin/subscriptions/"

    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="billing-admin",
            email="billing-admin@example.com",
            password="test-password",
        )
        self.client.force_authenticate(user=self.admin)
        self.plan = self.create_plan()
        self.tenant_id = uuid.uuid4()

    def test_admin_can_create_subscription(self):
        response = self.client.post(
            self.list_url,
            data={"tenant_id": str(self.tenant_id), "plan_id": str(self.plan.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, getattr(response, "data", response.content))
        self.assertEqual(response.data["tenant_id"], str(self.tenant_id))

    def test_non_admin_cannot_create_subscription(self):
        client = APIClient()
        response = client.post(
            self.list_url,
            data={"tenant_id": str(self.tenant_id), "plan_id": str(self.plan.id)},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_admin_can_cancel_subscription_immediately(self):
        subscription = self.create_subscription(plan=self.plan, tenant_id=self.tenant_id)
        response = self.client.post(
            f"/api/v1/admin/subscriptions/{subscription.id}/cancel/",
            data={"at_period_at": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200, getattr(response, "data", response.content))
        self.assertEqual(response.data["status"], Subscription.Status.CANCELED)

    def test_admin_can_renew_subscription(self):
        subscription = self.create_subscription(plan=self.plan, tenant_id=self.tenant_id)
        response = self.client.post(
            f"/api/v1/admin/subscriptions/{subscription.id}/renew/",
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, 200, getattr(response, "data", response.content))

class SubscriptionAdminPermissionTests(SubscriptionTestDataMixin, TestCase):
    def test_authenticated_non_admin_is_forbidden(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="regular-user",
            email="regular@example.com",
            password="test-password",
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/admin/subscriptions/",
            data={"tenant_id": str(uuid.uuid4()), "plan_id": str(self.create_plan().id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
