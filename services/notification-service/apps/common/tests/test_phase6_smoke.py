from unittest.mock import patch
from apps.common.async_service import (
    AsyncIntegrationService,
)
from apps.common.event_publishers import (
    EventPublisher,
)

class TestPhase6Smoke:

    @patch(
        "apps.common.event_publishers.AsyncIntegrationService.dispatch_event"
    )
    def test_notification_pipeline(
        self,
        dispatch_event,
    ):

        EventPublisher.user_invited(
            tenant_id="tenant-123",
            user_id="user-123",
            invitation_id="invitation-123",
        )

        dispatch_event.assert_called_once()

    @patch(
        "apps.common.async_service.AsyncJobDispatcher.dispatch_task"
    )
    def test_report_pipeline(
        self,
        dispatch_task,
    ):

        AsyncIntegrationService.generate_report(
            tenant_id="tenant-123",
            report_type="TENANT_ACTIVITY",
            requested_by="user-123",
        )

        dispatch_task.assert_called_once()

    @patch(
        "apps.common.async_service.AsyncJobDispatcher.dispatch_task"
    )
    def test_export_pipeline(
        self,
        dispatch_task,
    ):

        AsyncIntegrationService.generate_export(
            export_id="export-123",
        )

        dispatch_task.assert_called_once()