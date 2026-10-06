import uuid
import pytest
from unittest.mock import patch
from apps.reports.tasks import (
    generate_report,
    generate_scheduled_report,
)

@pytest.mark.django_db
class TestReportTasks:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_generate_report_task_is_registered(self):
        assert (
            generate_report.name
            == "apps.reports.tasks.generate_report"
        )

    def test_generate_report_task(self):
        result = generate_report.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "report_type": "TASK_SUMMARY",
                "requested_by": str(self.user_id),
            },
        )

        assert result.successful()

        assert result.result["status"] == "generated"

        assert (
            result.result["tenant_id"]
            == str(self.tenant_id)
        )

        assert (
            result.result["report_type"]
            == "TASK_SUMMARY"
        )

        assert (
            result.result["requested_by"]
            == str(self.user_id)
        )

    @patch(
        "apps.reports.tasks.ReportService.generate_report",
        side_effect=RuntimeError(
            "report generation failed"
        ),
    )
    def test_generate_report_task_propagates_failure(
        self,
        mock_generate,
    ):
        result = generate_report.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "report_type": "TASK_SUMMARY",
                "requested_by": str(self.user_id),
            },
        )

        assert result.failed()

        assert isinstance(
            result.result,
            RuntimeError,
        )

        mock_generate.assert_called_once_with(
            tenant_id=str(self.tenant_id),
            report_type="TASK_SUMMARY",
            requested_by=str(self.user_id),
        )

    def test_generate_report_task_without_user(self):
        result = generate_report.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "report_type": "PROJECT_SUMMARY",
            },
        )

        assert result.successful()

        assert (
            result.result["requested_by"]
            is None
        )

    def test_generate_report_task_rejects_invalid_type(
        self,
    ):
        result = generate_report.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "report_type": "INVALID",
            },
        )

        assert result.failed()

        assert isinstance(
            result.result,
            ValueError,
        )
        
    def test_scheduled_report_task_is_registered(self):
        assert (
            generate_scheduled_report.name
            == "apps.reports.tasks.generate_scheduled_report"
        )

    @patch(
        "apps.reports.tasks.generate_report",
    )
    def test_scheduled_report_delegates_to_report_task(
        self,
        mock_generate,
    ):
        mock_generate.return_value = {
            "status": "generated",
        }

        result = generate_scheduled_report.apply(
            kwargs={
                "tenant_id": str(self.tenant_id),
                "report_type": "TASK_SUMMARY",
            },
        )

        assert result.successful()

        mock_generate.assert_called_once_with(
            tenant_id=str(self.tenant_id),
            report_type="TASK_SUMMARY",
        )