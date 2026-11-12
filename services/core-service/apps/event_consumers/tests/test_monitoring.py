from unittest import TestCase
from unittest.mock import patch
from apps.event_consumers import monitoring

class EventConsumerMonitoringTests(TestCase):

    def test_record_processing_success(self):
        with patch.object(
            monitoring.EVENTS_PROCESSED,
            "labels",
        ) as labels:
            monitoring.record_processing_success(
                "tenant.created"
            )

            labels.assert_called_once_with(
                event_type="tenant.created"
            )

            labels.return_value.inc.assert_called_once()

    def test_record_processing_failure(self):
        with patch.object(
            monitoring.EVENTS_FAILED,
            "labels",
        ) as labels:
            monitoring.record_processing_failure(
                "tenant.suspended"
            )

            labels.return_value.inc.assert_called_once()

    def test_record_ignored_event(self):
        with patch.object(
            monitoring.EVENTS_IGNORED,
            "labels",
        ) as labels:
            monitoring.record_ignored_event(
                "member.joined"
            )

            labels.return_value.inc.assert_called_once()

    def test_record_dlq_event(self):
        with patch.object(
            monitoring.EVENTS_SENT_TO_DLQ,
            "labels",
        ) as labels:
            monitoring.record_dlq_event(
                "tenant.created"
            )

            labels.return_value.inc.assert_called_once()

    def test_record_replayed_event(self):
        with patch.object(
            monitoring.EVENTS_REPLAYED,
            "labels",
        ) as labels:
            monitoring.record_replayed_event(
                "tenant.created"
            )

            labels.return_value.inc.assert_called_once()

    def test_set_consumer_health(self):
        with patch.object(
            monitoring.CONSUMER_HEALTH,
            "set",
        ) as set_metric:

            monitoring.set_consumer_health(True)
            set_metric.assert_called_with(1)

            monitoring.set_consumer_health(False)
            set_metric.assert_called_with(0)

    def test_log_event(self):
        with patch.object(monitoring.logger, "log") as log:

            monitoring.log_event(
                20,
                "Kafka event processed",
                event_id="event-123",
                event_type="tenant.created",
                tenant_id="tenant-123",
                correlation_id="correlation-123",
                consumer_group="core-service-v1",
            )

            log.assert_called_once()