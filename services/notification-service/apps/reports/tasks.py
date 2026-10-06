import logging
from celery import Task, shared_task
from .services import ReportService

logger = logging.getLogger(__name__)

class ReportTask(Task):
    abstract = True

    def log_start(
        self,
        *,
        task_id,
        tenant_id,
        report_type,
    ):
        logger.info(
            "report_task_started",
            extra={
                "task_id": task_id,
                "tenant_id": str(tenant_id),
                "report_type": report_type,
            },
        )

    def log_success(
        self,
        *,
        task_id,
        tenant_id,
        report_type,
    ):
        logger.info(
            "report_task_completed",
            extra={
                "task_id": task_id,
                "tenant_id": str(tenant_id),
                "report_type": report_type,
            },
        )

    def log_failure(
        self,
        *,
        task_id,
        tenant_id,
        report_type,
        exc,
    ):
        logger.exception(
            "report_task_failed",
            extra={
                "task_id": task_id,
                "tenant_id": str(tenant_id),
                "report_type": report_type,
                "exception_type": type(exc).__name__,
            },
        )

@shared_task(
    bind=True,
    base=ReportTask,
    name="apps.reports.tasks.generate_report",
)
def generate_report(
    self,
    *,
    tenant_id,
    report_type,
    requested_by=None,
):
    self.log_start(
        task_id=self.request.id,
        tenant_id=tenant_id,
        report_type=report_type,
    )

    try:
        result = ReportService.generate_report(
            tenant_id=tenant_id,
            report_type=report_type,
            requested_by=requested_by,
        )
        self.log_success(
            task_id=self.request.id,
            tenant_id=tenant_id,
            report_type=report_type,
        )

        return result

    except Exception as exc:
        self.log_failure(
            task_id=self.request.id,
            tenant_id=tenant_id,
            report_type=report_type,
            exc=exc,
        )
        raise
    
@shared_task(
    bind=True,
    base=ReportTask,
    name="apps.reports.tasks.generate_scheduled_report",
)
def generate_scheduled_report(
    self,
    *,
    tenant_id,
    report_type,
):
    return generate_report(
        tenant_id=tenant_id,
        report_type=report_type,
    )