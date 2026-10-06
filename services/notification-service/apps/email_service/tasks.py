import logging
from celery import Task,shared_task
from .services import EmailService

logger = logging.getLogger(__name__)

class EmailTask(Task):
    """
    Base task for email processing.

    Retry behavior is intentionally not implemented here.
    Retry classification belongs to the dedicated retry module.
    """
    
    abstract = True
    
    def log_start(
        self,
        task_id: str,
        recipient: str,
    ):
        
        logger.info(
            "email_task_started",
            extra={
                "task_id": task_id,
                "recipient": recipient,
            },
        )
        
    def log_success(
        self,
        task_id: str,
        recipient: str,
    ):
        logger.info(
            "email_task_completed",
            extra={
                "task_id": task_id,
                "recipient": recipient,
            },
        )
        
    def log_failure(
        self,
        task_id: str,
        recipient: str,
        exc: Exception,
    ):
        logger.exception(
            "email_task_failed",
            extra={
                "task_id": task_id,
                "recipient": recipient,
                "exception_type": type(exc).__name__,
            },
        )

@shared_task(
    bind=True,
    base=EmailTask,
    name="apps.email_service.tasks.send_mail_task",
)
def send_email_task(
    self,
    recipient: str,
    subject: str,
    body: str,
):
    
    self.log_start(
        task_id=self.request.id,
        recipient=recipient
    )
    
    try:
        sent_count = EmailService.send_email(
            recipient=recipient,
            subject=subject,
            body=body,
        )
        
        self.log_success(
            task_id=self.request.id,
            recipient=recipient,
        )
        
        return {
            "status": "sent",
            "recipient": recipient,
            "sent_count": sent_count,
        }
        
    except Exception as exc:
        self.log_failure(
            task_id=self.request.id,
            recipient=recipient,
            exc=exc,
        )
        raise

@shared_task(
    bind=True,
    base=EmailTask,
    name="apps.email_service.tasks.send_welcome_email",
)
def send_welcome_email(
    self,
    recipient: str,
    user_name: str,
):
    self.log_start(
        task_id=self.request.id,
        recipient=recipient,
    )

    try:
        sent_count = EmailService.send_welcome_email(
            recipient=recipient,
            user_name=user_name,
        )

        self.log_success(
            task_id=self.request.id,
            recipient=recipient,
        )

        return {
            "status": "sent",
            "recipient": recipient,
            "sent_count": sent_count,
        }

    except Exception as exc:
        self.log_failure(
            task_id=self.request.id,
            recipient=recipient,
            exc=exc,
        )
        raise