import uuid
import pytest
from apps.reports.services import ReportService

class TestReportService:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_supported_report_types(self):
        assert "TENANT_ACTIVITY" in (
            ReportService.SUPPORTED_REPORTS
        )

        assert "TASK_SUMMARY" in (
            ReportService.SUPPORTED_REPORTS
        )

        assert "PROJECT_SUMMARY" in (
            ReportService.SUPPORTED_REPORTS
        )

    def test_generate_tenant_activity_report(self):
        result = ReportService.generate_report(
            tenant_id=self.tenant_id,
            report_type="TENANT_ACTIVITY",
            requested_by=self.user_id,
        )

        assert result["status"] == "generated"
        assert (
            result["tenant_id"]
            == str(self.tenant_id)
        )
        assert (
            result["report_type"]
            == "TENANT_ACTIVITY"
        )
        assert (
            result["requested_by"]
            == str(self.user_id)
        )
        assert "generated_at" in result
        assert result["data"]["record_count"] == 0

    def test_generate_task_summary_report(self):
        result = ReportService.generate_report(
            tenant_id=self.tenant_id,
            report_type="TASK_SUMMARY",
        )

        assert result["status"] == "generated"
        assert result["report_type"] == "TASK_SUMMARY"
        assert result["requested_by"] is None

    def test_generate_project_summary_report(self):
        result = ReportService.generate_report(
            tenant_id=self.tenant_id,
            report_type="PROJECT_SUMMARY",
        )

        assert result["status"] == "generated"
        assert result["report_type"] == "PROJECT_SUMMARY"

    def test_requires_tenant_id(self):
        with pytest.raises(ValueError):
            ReportService.generate_report(
                tenant_id=None,
                report_type="TASK_SUMMARY",
            )

    def test_requires_report_type(self):
        with pytest.raises(ValueError):
            ReportService.generate_report(
                tenant_id=self.tenant_id,
                report_type=None,
            )

    def test_rejects_unknown_report_type(self):
        with pytest.raises(ValueError):
            ReportService.generate_report(
                tenant_id=self.tenant_id,
                report_type="UNKNOWN_REPORT",
            )

    def test_validate_request_rejects_empty_tenant(self):
        with pytest.raises(ValueError):
            ReportService.validate_request(
                tenant_id=None,
                report_type="TASK_SUMMARY",
            )

    def test_validate_request_rejects_empty_report_type(self):
        with pytest.raises(ValueError):
            ReportService.validate_request(
                tenant_id=self.tenant_id,
                report_type=None,
            )

    def test_validate_request_rejects_unsupported_report(self):
        with pytest.raises(ValueError):
            ReportService.validate_request(
                tenant_id=self.tenant_id,
                report_type="INVALID",
            )