import logging
from celery.signals import task_failure

logger = logging.getLogger(__name__)

@task_failure.connect
def log_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    einfo=None,
    **extra,
):
    task_request = getattr(
        sender, "request", None
    )
    headers = getattr(
        task_request, "headers", None
    ) or {}

    log_extra = {
        "event": "celery.task.failed",
        "task_id": str(task_id) if task_id else "",
    }
    
    request_id = headers.get("request_id")
    if request_id:
        log_extra["request_id"] = request_id
        
    logger.error(
        "Celery task failed",
        extra=log_extra,
        exc_info=(
            type(exception),
            exception,
            getattr(einfo, "tb", None),
        ) if exception else None,
    )
