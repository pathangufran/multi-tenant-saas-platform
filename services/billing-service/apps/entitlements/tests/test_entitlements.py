"""Class-based tests for the entitlements app.

These tests use Django's TestCase (not pytest fixtures or function-based tests).
They target the models, serializers, and service APIs in the supplied files.
"""

import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from datetime import timedelta
from django.utils import timezone

from apps.entitlements.models import Feature, PlanFeature
from apps.entitlements.serializers import (
    FeatureCreateSerializer,
    FeatureUpdateSerializer,
    FeatureResponseSerializer,
    PlanFeatureCreateSerializer,
    PlanFeatureUpdateSerializer,
    PlanFeatureResponseSerializer,
    LimitCheckSerializer,
    TenantEntitlementsSerializer,
    LimitCheckResultSerializer,
)
from apps.entitlements.services import EntitlementService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription


class EntitlementTestDataMixin:
    """Shared factories for Django TestCase classes."""

    def create_plan(self, **overrides):
        values = {
            "code": "PRO",
            "name": "Professional",
            "description": "Professional plan",
            "price": Decimal("999.00"),
            "currency": "INR",
            "billing_interval": Plan.BillingInterval.MONTHLY,
            "is_active": True,
            "is_public": True,
        }
        values.update(overrides)
        return Plan.objects.create(**values)

    def create_feature(self, **overrides):
        values = {
            "key": "max_users",
            "name": "Maximum users",
            "description": "Maximum number of active users.",
            "value_type": Feature.ValueType.INTEGER,
            "is_active": True,
        }
        values.update(overrides)
        return Feature.objects.create(**values)

    def create_subscription(self, plan, tenant_id=None, status=None):
        start = timezone.now()
        return Subscription.objects.create(
            tenant_id=tenant_id or uuid.uuid4(),
            plan=plan,
            status=status or Subscription.Status.ACTIVE,
            start_at=start,
            current_period_start=start,
            current_period_end=start + timedelta(days=30),
        )

    def create_admin_client(self):
        user_model = get_user_model()
        user = user_model.objects.create_superuser(
            username="entitlements-admin",
            email="entitlements-admin@example.com",
            password="test-password",
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client


class FeatureModelTests(EntitlementTestDataMixin, TestCase):
    def test_feature_is_created_with_uuid_and_defaults(self):
        feature = self.create_feature()

        self.assertIsNotNone(feature.id)
        self.assertEqual(feature.key, "max_users")
        self.assertTrue(feature.is_active)
        self.assertEqual(str(feature), "max_users")

    def test_feature_ordering_uses_key(self):
        self.create_feature(key="storage_limit", name="Storage", value_type=Feature.ValueType.STORAGE_BYTES)
        self.create_feature(key="advanced_reports", name="Reports", value_type=Feature.ValueType.BOOLEAN)

        self.assertEqual(
            list(Feature.objects.values_list("key", flat=True)),
            ["advanced_reports", "max_users", "storage_limit"],
        )

    def test_feature_key_must_be_unique(self):
        self.create_feature()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_feature(name="Duplicate")


class PlanFeatureModelTests(EntitlementTestDataMixin, TestCase):
    def setUp(self):
        self.plan = self.create_plan()
        self.feature = self.create_feature()

    def test_plan_feature_relationship_and_string_representation(self):
        assignment = PlanFeature.objects.create(
            plan=self.plan, feature=self.feature, enabled=True, value=25
        )

        self.assertEqual(assignment.plan_id, self.plan.id)
        self.assertEqual(assignment.feature_id, self.feature.id)
        self.assertEqual(str(assignment), "PRO - max_users")

    def test_duplicate_plan_feature_pair_is_rejected(self):
        PlanFeature.objects.create(plan=self.plan, feature=self.feature, value=25)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlanFeature.objects.create(plan=self.plan, feature=self.feature, value=50)

    def test_disabled_feature_cannot_have_value(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlanFeature.objects.create(
                    plan=self.plan, feature=self.feature, enabled=False, value=10
                )

    def test_disabled_feature_may_have_null_value(self):
        assignment = PlanFeature.objects.create(
            plan=self.plan, feature=self.feature, enabled=False, value=None
        )
        self.assertFalse(assignment.enabled)
        self.assertIsNone(assignment.value)


class FeatureSerializerTests(EntitlementTestDataMixin, TestCase):
    def test_create_serializer_accepts_valid_feature(self):
        serializer = FeatureCreateSerializer(data={
            "key": "max_users",
            "name": "Maximum users",
            "description": "Limit active users",
            "value_type": Feature.ValueType.INTEGER,
            "is_active": True,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["key"], "max_users")

    def test_create_serializer_normalizes_key(self):
        serializer = FeatureCreateSerializer(data={
            "key": "  MAX_USERS  ",
            "name": "Maximum users",
            "value_type": Feature.ValueType.INTEGER,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["key"], "max_users")

    def test_create_serializer_rejects_invalid_key(self):
        serializer = FeatureCreateSerializer(data={
            "key": "invalid key!",
            "name": "Invalid",
            "value_type": Feature.ValueType.BOOLEAN,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("key", serializer.errors)

    def test_create_serializer_rejects_invalid_value_type(self):
        serializer = FeatureCreateSerializer(data={
            "key": "max_users",
            "name": "Maximum users",
            "value_type": "STRING",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("value_type", serializer.errors)

    def test_create_serializer_rejects_duplicate_key(self):
        self.create_feature()
        serializer = FeatureCreateSerializer(data={
            "key": "max_users",
            "name": "Duplicate",
            "value_type": Feature.ValueType.INTEGER,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("key", serializer.errors)

    def test_update_serializer_validates_fields(self):
        serializer = FeatureUpdateSerializer(data={
            "key": "max_projects",
            "name": "Maximum projects",
            "value_type": Feature.ValueType.INTEGER,
        }, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_response_serializer_exposes_model_fields(self):
        feature = self.create_feature()
        data = FeatureResponseSerializer(feature).data
        self.assertEqual(data["id"], str(feature.id))
        self.assertEqual(data["key"], "max_users")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)


class PlanFeatureSerializerTests(EntitlementTestDataMixin, TestCase):
    def setUp(self):
        self.plan = self.create_plan()
        self.integer_feature = self.create_feature()
        self.boolean_feature = self.create_feature(
            key="advanced_reports",
            name="Advanced reports",
            value_type=Feature.ValueType.BOOLEAN,
        )

    def test_create_serializer_accepts_integer_value(self):
        serializer = PlanFeatureCreateSerializer(data={
            "plan_id": str(self.plan.id),
            "feature_id": str(self.integer_feature.id),
            "enabled": True,
            "value": 50,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["value"], 50)

    def test_create_serializer_accepts_boolean_value(self):
        serializer = PlanFeatureCreateSerializer(data={
            "plan_id": str(self.plan.id),
            "feature_id": str(self.boolean_feature.id),
            "enabled": True,
            "value": True,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_serializer_rejects_boolean_for_integer_feature(self):
        serializer = PlanFeatureCreateSerializer(data={
            "plan_id": str(self.plan.id),
            "feature_id": str(self.integer_feature.id),
            "enabled": True,
            "value": True,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("value", serializer.errors)

    def test_create_serializer_rejects_negative_integer(self):
        serializer = PlanFeatureCreateSerializer(data={
            "plan_id": str(self.plan.id),
            "feature_id": str(self.integer_feature.id),
            "enabled": True,
            "value": -1,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("value", serializer.errors)

    def test_create_serializer_rejects_value_for_disabled_feature(self):
        serializer = PlanFeatureCreateSerializer(data={
            "plan_id": str(self.plan.id),
            "feature_id": str(self.integer_feature.id),
            "enabled": False,
            "value": 10,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("value", serializer.errors)

    def test_update_serializer_accepts_valid_payload(self):
        serializer = PlanFeatureUpdateSerializer(data={
            "plan_id": str(self.plan.id),
            "feature_id": str(self.integer_feature.id),
            "enabled": True,
            "value": 75,
        }, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_response_serializer_exposes_assignment_fields(self):
        assignment = PlanFeature.objects.create(
            plan=self.plan, feature=self.integer_feature, enabled=True, value=50
        )
        data = PlanFeatureResponseSerializer(assignment).data
        self.assertEqual(data["id"], str(assignment.id))
        self.assertEqual(data["plan_id"], str(self.plan.id))
        self.assertEqual(data["feature_id"], str(self.integer_feature.id))
        self.assertEqual(data["value"], 50)


class EntitlementServiceFeatureTests(EntitlementTestDataMixin, TestCase):
    def test_create_feature_persists_data(self):
        feature = EntitlementService.create_feature(data={
            "key": "max_users",
            "name": "Maximum users",
            "description": "Maximum active users",
            "value_type": Feature.ValueType.INTEGER,
            "is_active": True,
        })
        self.assertEqual(feature.key, "max_users")
        self.assertEqual(Feature.objects.count(), 1)

    def test_list_features_excludes_inactive_by_default(self):
        self.create_feature()
        self.create_feature(
            key="legacy_feature", name="Legacy", value_type=Feature.ValueType.BOOLEAN,
            is_active=False,
        )
        self.assertEqual(
            list(EntitlementService.list_features().values_list("key", flat=True)),
            ["max_users"],
        )

    def test_list_features_can_include_inactive(self):
        self.create_feature()
        self.create_feature(
            key="legacy_feature", name="Legacy", value_type=Feature.ValueType.BOOLEAN,
            is_active=False,
        )
        self.assertEqual(EntitlementService.list_features(active_only=False).count(), 2)

    def test_update_feature_changes_supplied_fields(self):
        feature = self.create_feature()
        updated = EntitlementService.update_feature(
            feature_id=feature.id, data={"name": "Maximum active users"}
        )
        self.assertEqual(updated.name, "Maximum active users")
        self.assertEqual(updated.key, feature.key)

    def test_update_unknown_feature_raises_value_error(self):
        with self.assertRaisesMessage(ValueError, "Feature not found."):
            EntitlementService.update_feature(feature_id=uuid.uuid4(), data={"name": "Missing"})


class EntitlementServicePlanFeatureTests(EntitlementTestDataMixin, TestCase):
    def setUp(self):
        self.plan = self.create_plan()
        self.integer_feature = self.create_feature()
        self.boolean_feature = self.create_feature(
            key="advanced_reports", name="Advanced reports",
            value_type=Feature.ValueType.BOOLEAN,
        )

    def test_set_integer_entitlement(self):
        assignment = EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.integer_feature.id, value=50
        )
        self.assertTrue(assignment.enabled)
        self.assertEqual(assignment.value, 50)

    def test_set_boolean_entitlement(self):
        assignment = EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.boolean_feature.id, value=True
        )
        self.assertIs(assignment.value, True)

    def test_setting_existing_entitlement_updates_in_place(self):
        first = EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.integer_feature.id, value=50
        )
        second = EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.integer_feature.id, value=75
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.value, 75)
        self.assertEqual(PlanFeature.objects.filter(plan=self.plan, feature=self.integer_feature).count(), 1)

    def test_rejects_wrong_value_type(self):
        with self.assertRaisesMessage(ValueError, "Value does not match feature type."):
            EntitlementService.set_plan_feature(
                plan_id=self.plan.id, feature_id=self.integer_feature.id, value=True
            )

    def test_rejects_negative_integer(self):
        with self.assertRaisesMessage(ValueError, "Value does not match feature type."):
            EntitlementService.set_plan_feature(
                plan_id=self.plan.id, feature_id=self.integer_feature.id, value=-1
            )

    def test_rejects_value_when_disabled(self):
        with self.assertRaisesMessage(ValueError, "Disabled features must not have a value."):
            EntitlementService.set_plan_feature(
                plan_id=self.plan.id, feature_id=self.integer_feature.id,
                enabled=False, value=10,
            )

    def test_rejects_unknown_plan(self):
        with self.assertRaisesMessage(ValueError, "Plan not found."):
            EntitlementService.set_plan_feature(
                plan_id=uuid.uuid4(), feature_id=self.integer_feature.id, value=10
            )

    def test_rejects_unknown_feature(self):
        with self.assertRaisesMessage(ValueError, "Feature not found."):
            EntitlementService.set_plan_feature(
                plan_id=self.plan.id, feature_id=uuid.uuid4(), value=10
            )

    def test_rejects_inactive_feature(self):
        self.integer_feature.is_active = False
        self.integer_feature.save(update_fields=["is_active", "updated_at"])
        with self.assertRaisesMessage(ValueError, "Feature not found."):
            EntitlementService.set_plan_feature(
                plan_id=self.plan.id, feature_id=self.integer_feature.id, value=10
            )

    def test_list_plan_features_orders_by_feature_key(self):
        EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.integer_feature.id, value=10
        )
        EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.boolean_feature.id, value=True
        )
        self.assertEqual(
            list(EntitlementService.list_plan_features(plan_id=self.plan.id).values_list("feature__key", flat=True)),
            ["advanced_reports", "max_users"],
        )

    def test_get_plan_feature_returns_assignment(self):
        assignment = EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=self.integer_feature.id, value=10
        )
        result = EntitlementService.get_plan_feature(
            plan_id=self.plan.id, feature_id=self.integer_feature.id
        )
        self.assertEqual(result.id, assignment.id)

    def test_get_missing_plan_feature_raises_value_error(self):
        with self.assertRaisesMessage(ValueError, "Plan feature not found."):
            EntitlementService.get_plan_feature(
                plan_id=self.plan.id, feature_id=uuid.uuid4()
            )


class EntitlementQuerySerializerTests(TestCase):
    def test_limit_check_serializer_validates_and_normalizes_key(self):
        tenant_id = uuid.uuid4()
        serializer = LimitCheckSerializer(data={
            "tenant_id": str(tenant_id),
            "feature_key": "  MAX_USERS  ",
            "requested_quantity": 3,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["feature_key"], "max_users")
        self.assertEqual(serializer.validated_data["requested_quantity"], 3)

    def test_limit_check_serializer_rejects_zero_quantity(self):
        serializer = LimitCheckSerializer(data={
            "tenant_id": str(uuid.uuid4()),
            "feature_key": "max_users",
            "requested_quantity": 0,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("requested_quantity", serializer.errors)

    def test_tenant_entitlements_serializer_accepts_no_subscription(self):
        serializer = TenantEntitlementsSerializer(data={
            "tenant_id": str(uuid.uuid4()),
            "has_subscription": False,
            "plan": None,
            "features": {},
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_limit_check_result_serializer_accepts_result(self):
        serializer = LimitCheckResultSerializer(data={
            "allowed": True,
            "reason": "within_limit",
            "feature_key": "max_users",
            "limit": 50,
            "current_usage": 20,
            "requested_quantity": 1,
            "remaining": 30,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TenantEntitlementServiceTests(EntitlementTestDataMixin, TestCase):
    def setUp(self):
        self.plan = self.create_plan()
        self.tenant_id = uuid.uuid4()

    def test_tenant_without_subscription_returns_empty_entitlements(self):
        # The service's current implementation raises DoesNotExist for this case;
        # this test documents the intended API contract and will expose that defect.
        result = EntitlementService.get_tenant_entitlements(tenant_id=self.tenant_id)
        self.assertEqual(result["tenant_id"], str(self.tenant_id))
        self.assertFalse(result["has_subscription"])
        self.assertIsNone(result["plan"])
        self.assertEqual(result["features"], {})

    def test_active_subscription_returns_plan_entitlements(self):
        subscription = self.create_subscription(self.plan, tenant_id=self.tenant_id)
        feature = self.create_feature()
        EntitlementService.set_plan_feature(
            plan_id=self.plan.id, feature_id=feature.id, value=50
        )

        result = EntitlementService.get_tenant_entitlements(tenant_id=self.tenant_id)
        self.assertEqual(result["has_subscription"],False)
        self.assertEqual(result["plan"]["code"], self.plan.code)
        self.assertEqual(result["features"]["max_users"], 50)

