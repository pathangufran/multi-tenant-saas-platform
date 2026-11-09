import uuid
from unittest.mock import MagicMock, patch
import pytest
from django.db import transaction
from apps.outbox.models import OutboxEvent
from apps.outbox.publisher import OutboxPublisher
from apps.outbox.tasks import publish_outbox_events
from apps.tenants.models import Tenant, TenantMembership
from apps.tenants.services import TenantService

@pytest.mark.django_db
class TestTenantEventIntegration:

    def setup_method(self):
        self.owner_user_id = uuid.uuid4()

    def test_tenant_creation_persists_events_atomically(self):
        tenant = TenantService.create_tenant(
            name="Integration Corporation",
            slug=f"integration-{uuid.uuid4().hex[:8]}",
            owner_user_id=self.owner_user_id,
        )

        events = OutboxEvent.objects.filter(
            tenant_id=tenant.id,
        ).order_by("event_type")

        assert events.count() == 2

        event_types = set(
            events.values_list("event_type", flat=True)
        )

        assert event_types == {
            "tenant.created",
            "member.joined",
        }

        membership = TenantMembership.objects.get(
            tenant=tenant,
            user_id=self.owner_user_id,
        )

        assert membership.status == TenantMembership.Status.ACTIVE

    def test_tenant_creation_rollback_removes_all_events(self):
        with patch(
            "apps.tenants.services.OutboxService.record_event",
            side_effect=RuntimeError("simulated failure"),
        ):
            with pytest.raises(
                RuntimeError,
                match="simulated failure",
            ):
                TenantService.create_tenant(
                    name="Rollback Corporation",
                    slug=f"rollback-{uuid.uuid4().hex[:8]}",
                    owner_user_id=self.owner_user_id,
                )

        assert Tenant.objects.count() == 0
        assert TenantMembership.objects.count() == 0
        assert OutboxEvent.objects.count() == 0

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_celery_task_publishes_tenant_events(
        self,
        kafka_producer_class,
    ):
        TenantService.create_tenant(
            name="Publishing Corporation",
            slug=f"publishing-{uuid.uuid4().hex[:8]}",
            owner_user_id=self.owner_user_id,
        )

        producer = MagicMock()
        future = MagicMock()
        future.get.return_value = None
        producer.send.return_value = future

        kafka_producer_class.return_value = producer

        result = publish_outbox_events.run()

        assert result["claimed"] == 2
        assert result["published"] == 2
        assert result["failed"] == 0

        assert OutboxEvent.objects.filter(
            status=OutboxEvent.Status.PUBLISHED,
        ).count() == 2

        assert producer.send.call_count == 2

    @patch("apps.outbox.publisher.KafkaProducer")
    def test_kafka_failure_does_not_mark_event_published(
        self,
        kafka_producer_class,
    ):
        TenantService.create_tenant(
            name="Failure Corporation",
            slug=f"failure-{uuid.uuid4().hex[:8]}",
            owner_user_id=self.owner_user_id,
        )

        producer = MagicMock()
        future = MagicMock()
        future.get.side_effect = TimeoutError(
            "Kafka unavailable"
        )
        producer.send.return_value = future

        kafka_producer_class.return_value = producer

        result = OutboxPublisher.publish_pending_events()

        assert result["claimed"] == 2
        assert result["published"] == 0
        assert result["failed"] == 2

        assert OutboxEvent.objects.filter(
            status=OutboxEvent.Status.PENDING,
        ).count() == 2

        assert OutboxEvent.objects.filter(
            published_at__isnull=False,
        ).count() == 0

    def test_published_event_is_not_claimed_again(self):
        TenantService.create_tenant(
            name="Already Published Corporation",
            slug=f"published-{uuid.uuid4().hex[:8]}",
            owner_user_id=self.owner_user_id,
        )

        OutboxEvent.objects.update(
            status=OutboxEvent.Status.PUBLISHED,
        )

        with patch(
            "apps.outbox.publisher.KafkaProducer"
        ) as kafka_producer_class:

            producer = MagicMock()
            kafka_producer_class.return_value = producer

            result = OutboxPublisher.publish_pending_events()

        assert result["claimed"] == 0
        assert result["published"] == 0
        producer.send.assert_not_called()
