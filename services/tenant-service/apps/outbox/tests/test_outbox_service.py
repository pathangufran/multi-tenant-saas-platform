import pytest
from django.db import transaction
from apps.outbox.models import OutboxEvent
from apps.outbox.services import OutboxService

@pytest.mark.django_db
class TestOutboxService:

    def test_record_event_creates_pending_event(self):
        event = OutboxService.record_event(
            event_type="tenant.created",
            aggregate_type="tenant",
            aggregate_id="tenant-123",
            tenant_id="11111111-1111-4111-8111-111111111111",
            aggregate_version=1,
            data={
                "tenant_id": "11111111-1111-4111-8111-111111111111",
                "name": "Acme",
            },
        )

        assert OutboxEvent.objects.count() == 1
        assert event.event_type == "tenant.created"
        assert event.producer == "tenant-service"
        assert event.aggregate_type == "tenant"
        assert event.aggregate_id == "tenant-123"
        assert event.aggregate_version == 1
        assert event.status == OutboxEvent.Status.PENDING
        assert event.attempts == 0
        assert event.published_at is None

    def test_record_event_requires_active_transaction(self):
        with pytest.raises(
            RuntimeError,
            match="active database transaction",
        ):
            OutboxService.record_event(
                event_type="tenant.created",
                aggregate_type="tenant",
                aggregate_id="tenant-123",
                data={},
            )

        assert OutboxEvent.objects.count() == 0

    def test_event_is_rolled_back_with_business_transaction(self):
        with pytest.raises(RuntimeError, match="rollback"):
            with transaction.atomic():
                OutboxService.record_event(
                    event_type="tenant.created",
                    aggregate_type="tenant",
                    aggregate_id="tenant-123",
                    data={"name": "Acme"},
                )

                raise RuntimeError("rollback")

        assert OutboxEvent.objects.count() == 0

    def test_record_event_rejects_non_dictionary_data(self):
        with pytest.raises(
            ValueError,
            match="dictionary",
        ):
            with transaction.atomic():
                OutboxService.record_event(
                    event_type="tenant.created",
                    aggregate_type="tenant",
                    aggregate_id="tenant-123",
                    data=["invalid"],
                )

        assert OutboxEvent.objects.count() == 0

    def test_record_event_rejects_missing_event_type(self):
        with pytest.raises(
            ValueError,
            match="event_type is required",
        ):
            with transaction.atomic():
                OutboxService.record_event(
                    event_type=" ",
                    aggregate_type="tenant",
                    aggregate_id="tenant-123",
                    data={},
                )

        assert OutboxEvent.objects.count() == 0

    def test_record_event_rejects_invalid_aggregate_version(self):
        with pytest.raises(
            ValueError,
            match="aggregate_version",
        ):
            with transaction.atomic():
                OutboxService.record_event(
                    event_type="tenant.created",
                    aggregate_type="tenant",
                    aggregate_id="tenant-123",
                    aggregate_version=0,
                    data={},
                )

        assert OutboxEvent.objects.count() == 0
