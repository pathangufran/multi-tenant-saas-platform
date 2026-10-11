import uuid
import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.usage_tracking.models import UsageRecord
from apps.usage_tracking.serializers import (
    UsageAdjustmentSerializer,
    UsageQuerySerializer,
    UsageRecordSerializer,
    UsageSetSerializer,
)
from apps.usage_tracking.services import UsageService

@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def second_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def usage_record(tenant_id):
    return UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=10,
        source="tenant-service",
    )


@pytest.fixture
def admin_client(db):
    user_model = get_user_model()
    user = user_model.objects.create_superuser(
        username="usage-admin",
        email="usage-admin@example.com",
        password="test-password",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_set_usage_creates_record(tenant_id):
    record = UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=10,
        source="tenant-service",
    )

    assert record.id is not None
    assert record.tenant_id == tenant_id
    assert record.metric == UsageRecord.Metric.ACTIVE_USERS
    assert record.quantity == 10
    assert record.source == "tenant-service"


@pytest.mark.django_db
def test_set_usage_updates_existing_record(usage_record, tenant_id):
    original_id = usage_record.id

    updated = UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=15,
        source="tenant-service",
    )

    assert updated.id == original_id
    assert updated.quantity == 15
    assert UsageRecord.objects.filter(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
    ).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("metric", "quantity"),
    [
        (UsageRecord.Metric.ACTIVE_USERS, 12),
        (UsageRecord.Metric.PROJECTS, 7),
        (UsageRecord.Metric.STORAGE_BYTES, 1024 * 1024),
    ],
)
def test_set_usage_supports_all_metrics(tenant_id, metric, quantity):
    record = UsageService.set_usage(
        tenant_id=tenant_id,
        metric=metric,
        quantity=quantity,
    )

    assert record.metric == metric
    assert record.quantity == quantity


@pytest.mark.django_db
def test_set_usage_rejects_negative_quantity(tenant_id):
    with pytest.raises(ValidationError):
        UsageService.set_usage(
            tenant_id=tenant_id,
            metric=UsageRecord.Metric.PROJECTS,
            quantity=-1,
        )


@pytest.mark.django_db
def test_set_usage_rejects_invalid_metric(tenant_id):
    with pytest.raises(ValidationError):
        UsageService.set_usage(
            tenant_id=tenant_id,
            metric="INVALID_METRIC",
            quantity=1,
        )


@pytest.mark.django_db
def test_adjust_usage_increases_quantity(usage_record, tenant_id):
    updated = UsageService.adjust_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        delta=3,
        source="tenant-service",
    )

    assert updated.quantity == 13


@pytest.mark.django_db
def test_adjust_usage_decreases_quantity(usage_record, tenant_id):
    updated = UsageService.adjust_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        delta=-4,
        source="tenant-service",
    )

    assert updated.quantity == 6


@pytest.mark.django_db
def test_adjust_usage_can_create_initial_record(tenant_id):
    updated = UsageService.adjust_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.PROJECTS,
        delta=2,
        source="core-service",
    )

    assert updated.quantity == 2
    assert updated.source == "core-service"


@pytest.mark.django_db
def test_adjust_usage_rejects_result_below_zero(usage_record, tenant_id):
    with pytest.raises(ValidationError):
        UsageService.adjust_usage(
            tenant_id=tenant_id,
            metric=UsageRecord.Metric.ACTIVE_USERS,
            delta=-11,
        )

    usage_record.refresh_from_db()
    assert usage_record.quantity == 10


@pytest.mark.django_db
def test_adjust_usage_rejects_zero_delta(tenant_id):
    with pytest.raises(ValidationError):
        UsageService.adjust_usage(
            tenant_id=tenant_id,
            metric=UsageRecord.Metric.PROJECTS,
            delta=0,
        )


@pytest.mark.django_db
def test_adjust_usage_rejects_invalid_metric(tenant_id):
    with pytest.raises(ValidationError):
        UsageService.adjust_usage(
            tenant_id=tenant_id,
            metric="INVALID_METRIC",
            delta=1,
        )


@pytest.mark.django_db
def test_list_usage_returns_only_requested_tenant(
    tenant_id,
    second_tenant_id,
):
    UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=5,
    )
    UsageService.set_usage(
        tenant_id=second_tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=20,
    )

    records = UsageService.list_usage(tenant_id=tenant_id)

    assert records.count() == 1
    assert records.first().tenant_id == tenant_id
    assert records.first().quantity == 5


@pytest.mark.django_db
def test_get_usage_returns_record(usage_record, tenant_id):
    result = UsageService.get_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
    )

    assert result is not None
    assert result.id == usage_record.id


@pytest.mark.django_db
def test_get_usage_returns_none_when_missing(tenant_id):
    result = UsageService.get_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.PROJECTS,
    )

    assert result is None


@pytest.mark.django_db
def test_set_serializer_validates_valid_data(tenant_id):
    serializer = UsageSetSerializer(
        data={
            "tenant_id": str(tenant_id),
            "metric": UsageRecord.Metric.ACTIVE_USERS,
            "quantity": 10,
            "source": "tenant-service",
        }
    )

    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_set_serializer_rejects_negative_quantity(tenant_id):
    serializer = UsageSetSerializer(
        data={
            "tenant_id": str(tenant_id),
            "metric": UsageRecord.Metric.ACTIVE_USERS,
            "quantity": -1,
        }
    )

    assert not serializer.is_valid()
    assert "quantity" in serializer.errors


@pytest.mark.django_db
def test_set_serializer_rejects_invalid_metric(tenant_id):
    serializer = UsageSetSerializer(
        data={
            "tenant_id": str(tenant_id),
            "metric": "UNKNOWN",
            "quantity": 10,
        }
    )

    assert not serializer.is_valid()
    assert "metric" in serializer.errors


@pytest.mark.django_db
def test_adjustment_serializer_rejects_zero_delta(tenant_id):
    serializer = UsageAdjustmentSerializer(
        data={
            "tenant_id": str(tenant_id),
            "metric": UsageRecord.Metric.PROJECTS,
            "delta": 0,
        }
    )

    assert not serializer.is_valid()
    assert "delta" in serializer.errors


@pytest.mark.django_db
def test_query_serializer_rejects_invalid_tenant_id():
    serializer = UsageQuerySerializer(
        data={"tenant_id": "not-a-uuid"}
    )

    assert not serializer.is_valid()
    assert "tenant_id" in serializer.errors


@pytest.mark.django_db
def test_usage_record_serializer_is_read_only(usage_record):
    serializer = UsageRecordSerializer(usage_record)

    assert serializer.data["id"] == str(usage_record.id)
    assert serializer.data["quantity"] == 10
    assert serializer.data["metric"] == UsageRecord.Metric.ACTIVE_USERS


@pytest.mark.django_db
def test_admin_can_set_usage(admin_client, tenant_id):
    response = admin_client.post(
        "/api/v1/admin/usage/",
        data={
            "tenant_id": str(tenant_id),
            "metric": UsageRecord.Metric.PROJECTS,
            "quantity": 4,
            "source": "core-service",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["quantity"] == 4
    assert response.data["source"] == "core-service"


@pytest.mark.django_db
def test_admin_can_list_usage(admin_client, usage_record, tenant_id):
    response = admin_client.get(
        "/api/v1/admin/usage/",
        {"tenant_id": str(tenant_id)},
    )

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["quantity"] == 10


@pytest.mark.django_db
def test_usage_list_requires_tenant_id(admin_client):
    response = admin_client.get("/api/v1/admin/usage/")

    assert response.status_code == 400
    assert "tenant_id" in response.data


@pytest.mark.django_db
def test_admin_can_adjust_usage(admin_client, tenant_id):
    UsageService.set_usage(
        tenant_id=tenant_id,
        metric=UsageRecord.Metric.ACTIVE_USERS,
        quantity=10,
    )

    response = admin_client.post(
        "/api/v1/admin/usage/adjust/",
        data={
            "tenant_id": str(tenant_id),
            "metric": UsageRecord.Metric.ACTIVE_USERS,
            "delta": 2,
            "source": "tenant-service",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["quantity"] == 12


@pytest.mark.django_db
def test_non_admin_cannot_set_usage(tenant_id):
    response = APIClient().post(
        "/api/v1/admin/usage/",
        data={
            "tenant_id": str(tenant_id),
            "metric": UsageRecord.Metric.PROJECTS,
            "quantity": 3,
        },
        format="json",
    )

    assert response.status_code in (401, 403)