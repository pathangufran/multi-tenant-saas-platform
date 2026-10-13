import uuid
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from apps.entitlements.models import Feature, PlanFeature
from apps.entitlements.serializers import (
    FeatureSerializer,
    PlanFeatureSerializer,
)
from apps.entitlements.services import EntitlementService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from apps.usage_tracking.models import UsageRecord
from apps.usage_tracking.services import UsageService

@pytest.fixture
def tenant_id():
    return uuid.uuid4()

@pytest.fixture
def plan(db):
    return Plan.objects.create(
        code="PRO",
        name="Professional",
        price=Decimal("999.00"),
        currency="INR",
        billing_interval=Plan.BillingInterval.MONTHLY,
        is_active=True,
        is_public=True,
    )

@pytest.fixture
def active_subscription(plan, tenant_id):
    return SubscriptionService.create_subscription(
        validated_data={
            "tenant_id": tenant_id,
            "plan_id": plan.id,
        }
    )

@pytest.fixture
def max_users_feature(db):
    return Feature.objects.create(
        key="max_users",
        name="Maximum users",
        description="Maximum number of active users.",
        value_type=Feature.ValueType.INTEGER,
    )

@pytest.fixture
def max_projects_feature(db):
    return Feature.objects.create(
        key="max_projects",
        name="Maximum projects",
        value_type=Feature.ValueType.INTEGER,
    )

@pytest.fixture
def storage_feature(db):
    return Feature.objects.create(
        key="storage_limit",
        name="Storage limit",
        value_type=Feature.ValueType.STORAGE_BYTES,
    )

@pytest.fixture
def reports_feature(db):
    return Feature.objects.create(
        key="advanced_reports",
        name="Advanced reports",
        value_type=Feature.ValueType.BOOLEAN,
    )

@pytest.fixture
def admin_client(db):
    user_model = get_user_model()
    user = user_model.objects.create_superuser(
        username="entitlements-admin",
        email="entitlements-admin@example.com",
        password="test-password",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
def test_create_feature():
    feature = EntitlementService.create_feature(
        validated_data={
            "key": "max_users",
            "name": "Maximum users",
            "description": "Maximum active users.",
            "value_type": Feature.ValueType.INTEGER,
            "is_active": True,
        }
    )

    assert feature.id is not None
    assert feature.key == "max_users"
    assert feature.value_type == Feature.ValueType.INTEGER

@pytest.mark.django_db
def test_feature_serializer_normalizes_key():
    serializer = FeatureSerializer(
        data={
            "key": "  MAX_USERS  ",
            "name": "Maximum users",
            "value_type": Feature.ValueType.INTEGER,
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["key"] == "max_users"

@pytest.mark.django_db
def test_duplicate_feature_key_is_rejected(max_users_feature):
    serializer = FeatureSerializer(
        data={
            "key": "max_users",
            "name": "Duplicate feature",
            "value_type": Feature.ValueType.INTEGER,
        }
    )

    assert not serializer.is_valid()
    assert "key" in serializer.errors

@pytest.mark.django_db
def test_update_feature(max_users_feature):
    updated = EntitlementService.update_feature(
        feature_id=max_users_feature.id,
        validated_data={"name": "Maximum active users"},
    )

    assert updated.name == "Maximum active users"

@pytest.mark.django_db
def test_update_unknown_feature_fails():
    with pytest.raises(ValidationError):
        EntitlementService.update_feature(
            feature_id=999999,
            validated_data={"name": "Unknown"},
        )

@pytest.mark.django_db
def test_list_features_excludes_inactive_by_default(max_users_feature):
    Feature.objects.create(
        key="legacy_feature",
        name="Legacy feature",
        value_type=Feature.ValueType.BOOLEAN,
        is_active=False,
    )

    features = EntitlementService.list_features(active_only=True)

    assert list(features.values_list("key", flat=True)) == ["max_users"]

@pytest.mark.django_db
def test_set_integer_plan_feature(plan, max_users_feature):
    assignment = EntitlementService.set_plan_feature(
        plan_id=plan.id,
        feature_id=max_users_feature.id,
        enabled=True,
        value=50,
    )

    assert assignment.plan_id == plan.id
    assert assignment.feature_id == max_users_feature.id
    assert assignment.enabled is True
    assert assignment.value == 50

@pytest.mark.django_db
def test_set_boolean_plan_feature(plan, reports_feature):
    assignment = EntitlementService.set_plan_feature(
        plan_id=plan.id,
        feature_id=reports_feature.id,
        enabled=True,
        value=True,
    )

    assert assignment.value is True

@pytest.mark.django_db
def test_update_existing_plan_feature_instead_of_duplicating(
    plan,
    max_users_feature,
):
    first = EntitlementService.set_plan_feature(
        plan_id=plan.id,
        feature_id=max_users_feature.id,
        enabled=True,
        value=50,
    )

    second = EntitlementService.set_plan_feature(
        plan_id=plan.id,
        feature_id=max_users_feature.id,
        enabled=True,
        value=75,
    )

    assert second.id == first.id
    assert second.value == 75
    assert PlanFeature.objects.filter(
        plan=plan,
        feature=max_users_feature,
    ).count() == 1

@pytest.mark.django_db
def test_plan_feature_rejects_wrong_value_type(plan, max_users_feature):
    with pytest.raises(ValidationError):
        EntitlementService.set_plan_feature(
            plan_id=plan.id,
            feature_id=max_users_feature.id,
            value=True,
        )

@pytest.mark.django_db
def test_plan_feature_rejects_negative_limit(plan, max_users_feature):
    with pytest.raises(ValidationError):
        EntitlementService.set_plan_feature(
            plan_id=plan.id,
            feature_id=max_users_feature.id,
            value=-1,
        )

@pytest.mark.django_db
def test_disabled_plan_feature_must_not_have_value(plan, max_users_feature):
    with pytest.raises(ValidationError):
        EntitlementService.set_plan_feature(
            plan_id=plan.id,
            feature_id=max_users_feature.id,
            enabled=False,
            value=50,
        )

@pytest.mark.django_db
def test_unknown_plan_rejected(max_users_feature):
    with pytest.raises(ValidationError):
        EntitlementService.set_plan_feature(
            plan_id=uuid.uuid4(),
            feature_id=max_users_feature.id,
            value=50,
        )

@pytest.mark.django_db
def test_unknown_feature_rejected(plan):
    with pytest.raises(ValidationError):
        EntitlementService.set_plan_feature(
            plan_id=plan.id,
            feature_id=999999,
            value=50,
        )

@pytest.mark.django_db
def test_inactive_feature_cannot_be_assigned(plan, max_users_feature):
    max_users_feature.is_active = False
    max_users_feature.save(update_fields=["is_active", "updated_at"])

    with pytest.raises(ValidationError):
        EntitlementService.set_plan_feature(
            plan_id=plan.id,
            feature_id=max_users_feature.id,
            value=50,
        )

@pytest.mark.django_db
def test_list_plan_features(plan, max_users_feature, reports_feature):
    EntitlementService.set_plan_feature(
        plan_id=plan.id,
        feature_id=max_users_feature.id,
        value=50,
    )
    EntitlementService.set_plan_feature(
        plan_id=plan.id,
        feature_id=reports_feature.id,
        value=True,
    )

    records = EntitlementService.list_plan_features(plan_id=plan.id)

    assert records.count() == 2

@pytest.mark.django_db
def test_get_tenant_entitlements(active_subscription, tenant_id):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=Feature.objects.create(
            key="max_users",
            name="Maximum users",
            value_type=Feature.ValueType.INTEGER,
        ).id,
        value=50,
    )

    result = EntitlementService.get_tenant_entitlements(tenant_id=tenant_id)

    assert result["has_subscription"] is True
    assert result["plan"]["code"] == "PRO"
    assert result["features"]["max_users"] == 50

@pytest.mark.django_db
def test_tenant_without_subscription_has_no_entitlements(tenant_id):
    result = EntitlementService.get_tenant_entitlements(tenant_id=tenant_id)

    assert result["has_subscription"] is False
    assert result["plan"] is None
    assert result["features"] == {}

@pytest.mark.django_db
def test_disabled_feature_is_returned_as_false(
    active_subscription,
    max_users_feature,
):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=max_users_feature.id,
        enabled=False,
        value=None,
    )

    result = EntitlementService.get_tenant_entitlements(
        tenant_id=active_subscription.tenant_id,
    )

    assert result["features"]["max_users"] is False

@pytest.mark.django_db
def test_check_limit_allows_usage_within_limit(
    active_subscription,
    max_users_feature,
    tenant_id,
):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=max_users_feature.id,
        value=50,
    )
    UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=20,
    )

    result = EntitlementService.check_limit(
        tenant_id=tenant_id,
        feature_key="max_users",
        requested_quantity=1,
    )

    assert result["allowed"] is True
    assert result["reason"] == "within_limit"
    assert result["limit"] == 50
    assert result["current_usage"] == 20
    assert result["remaining"] == 30

@pytest.mark.django_db
def test_check_limit_rejects_request_exceeding_limit(
    active_subscription,
    max_users_feature,
    tenant_id,
):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=max_users_feature.id,
        value=10,
    )
    UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=10,
    )

    result = EntitlementService.check_limit(
        tenant_id=tenant_id,
        feature_key="max_users",
        requested_quantity=1,
    )

    assert result["allowed"] is False
    assert result["reason"] == "limit_exceeded"
    assert result["remaining"] == 0

@pytest.mark.django_db
def test_check_limit_handles_missing_usage_record(
    active_subscription,
    max_projects_feature,
    tenant_id,
):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=max_projects_feature.id,
        value=5,
    )

    result = EntitlementService.check_limit(
        tenant_id=tenant_id,
        feature_key="max_projects",
        requested_quantity=1,
    )

    assert result["allowed"] is True
    assert result["current_usage"] == 0
    assert result["remaining"] == 5

@pytest.mark.django_db
def test_check_limit_fails_closed_without_subscription(
    max_users_feature,
    tenant_id,
):
    result = EntitlementService.check_limit(
        tenant_id=tenant_id,
        feature_key="max_users",
    )

    assert result["allowed"] is False
    assert result["reason"] == "no_active_subscription"

@pytest.mark.django_db
def test_check_limit_fails_closed_for_unknown_feature(
    active_subscription,
    tenant_id,
):
    result = EntitlementService.check_limit(
        tenant_id=tenant_id,
        feature_key="unknown_limit",
    )

    assert result["allowed"] is False
    assert result["reason"] == "unknown_feature"

@pytest.mark.django_db
def test_check_limit_fails_closed_when_feature_not_assigned(
    active_subscription,
    max_users_feature,
    tenant_id,
):
    result = EntitlementService.check_limit(
        tenant_id=tenant_id,
        feature_key="max_users",
    )

    assert result["allowed"] is False
    assert result["reason"] == "feature_not_entitled"

@pytest.mark.django_db
def test_check_limit_rejects_zero_requested_quantity(
    active_subscription,
    max_users_feature,
    tenant_id,
):
    with pytest.raises(ValidationError):
        EntitlementService.check_limit(
            tenant_id=tenant_id,
            feature_key="max_users",
            requested_quantity=0,
        )

@pytest.mark.django_db
def test_feature_serializer_rejects_invalid_key():
    serializer = FeatureSerializer(
        data={
            "key": "invalid key!",
            "name": "Invalid",
            "value_type": Feature.ValueType.BOOLEAN,
        }
    )

    assert not serializer.is_valid()
    assert "key" in serializer.errors

@pytest.mark.django_db
def test_plan_feature_serializer_rejects_wrong_type(max_users_feature, plan):
    serializer = PlanFeatureSerializer(
        data={
            "plan_id": str(plan.id),
            "feature_id": max_users_feature.id,
            "enabled": True,
            "value": True,
        }
    )

    assert not serializer.is_valid()
    assert "value" in serializer.errors

@pytest.mark.django_db
def test_admin_can_create_feature(admin_client):
    response = admin_client.post(
        "/api/v1/admin/features/",
        data={
            "key": "max_users",
            "name": "Maximum users",
            "value_type": Feature.ValueType.INTEGER,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["key"] == "max_users"

@pytest.mark.django_db
def test_admin_can_assign_plan_feature(
    admin_client,
    plan,
    max_users_feature,
):
    response = admin_client.post(
        "/api/v1/admin/plan-features/",
        data={
            "plan_id": str(plan.id),
            "feature_id": max_users_feature.id,
            "enabled": True,
            "value": 50,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["value"] == 50

@pytest.mark.django_db
def test_admin_can_read_tenant_entitlements(
    admin_client,
    active_subscription,
    max_users_feature,
    tenant_id,
):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=max_users_feature.id,
        value=50,
    )

    response = admin_client.get(
        "/api/v1/admin/entitlements/",
        {"tenant_id": str(tenant_id)},
    )

    assert response.status_code == 200
    assert response.data["has_subscription"] is True
    assert response.data["features"]["max_users"] == 50

@pytest.mark.django_db
def test_admin_can_check_a_limit(
    admin_client,
    active_subscription,
    max_users_feature,
    tenant_id,
):
    EntitlementService.set_plan_feature(
        plan_id=active_subscription.plan_id,
        feature_id=max_users_feature.id,
        value=50,
    )

    response = admin_client.post(
        "/api/v1/admin/entitlements/check/",
        data={
            "tenant_id": str(tenant_id),
            "feature_key": "max_users",
            "requested_quantity": 1,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["allowed"] is True

@pytest.mark.django_db
def test_non_admin_cannot_check_limits(tenant_id):
    response = APIClient().post(
        "/api/v1/admin/entitlements/check/",
        data={
            "tenant_id": str(tenant_id),
            "feature_key": "max_users",
        },
        format="json",
    )

    assert response.status_code in (401, 403)