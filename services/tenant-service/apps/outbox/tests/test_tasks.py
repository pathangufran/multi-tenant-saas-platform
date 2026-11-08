import pytest
from unittest.mock import patch
from apps.outbox.tasks import publish_outbox_events

@pytest.mark.django_db
class TestOutboxTasks:

    @patch(
        "apps.outbox.tasks.OutboxPublisher.publish_pending_events"
    )
    def test_publish_outbox_events_calls_publisher(
        self,
        publisher_mock,
    ):
        expected_stats = {
            "claimed": 3,
            "published": 3,
            "failed": 0,
            "lease_lost": 0,
        }

        publisher_mock.return_value = expected_stats

        result = publish_outbox_events.run()

        publisher_mock.assert_called_once_with(
            batch_size=100,
        )

        assert result == expected_stats