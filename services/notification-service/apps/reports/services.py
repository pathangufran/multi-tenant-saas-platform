from datetime import datetime,timezone

class ReportService:
    
    SUPPORTED_REPORTS = {
        "TENANT_ACTIVITY",
        "TASK_SUMMARY",
        "PROJECT_SUMMARY",
    }

    @staticmethod
    def validate_request(
        *,
        tenant_id,
        report_type,
    ):
        
        if not tenant_id:
            raise ValueError(
                "tenant_id is required."
            )
        
        if not report_type:
            raise ValueError(
                "report_type is required."
            )
            
        if report_type not in ReportService.SUPPORTED_REPORTS:
            raise ValueError(
                f"Unsupported report type: {report_type}"
            )
            
    @staticmethod
    def generate_report(
        *,
        tenant_id,
        report_type,
        requested_by=None,
    ):
        ReportService.validate_request(
            tenant_id=tenant_id,
            report_type=report_type,
        )

        generated_at = datetime.now(
            timezone.utc,
        ).isoformat()

        return {
            "status": "generated",
            "tenant_id": str(tenant_id),
            "report_type": report_type,
            "requested_by": (
                str(requested_by)
                if requested_by
                else None
            ),
            "generated_at": generated_at,
            "data": {
                "records": [],
                "record_count": 0,
            },
        }