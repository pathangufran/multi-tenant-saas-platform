import logging
from celery import Task,shared_task
from .models import Notification
from .services import NotificationService

logger = logging.getLogger(__name__)

class NotificationTask(Task):
    abstract = True
    
    def log_start(
        self,
        *,
        task_id,
        tenant_id,
        user_id,
        event_type,
    ):
        logger.info(
            "notification_task_started",
            extra={
                "task_id": task_id,
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "event_type": event_type,
            },
        )

    def log_success(
        self,
        *,
        task_id,
        tenant_id,
        user_id,
        event_type,
    ):
        logger.info(
            "notification_task_completed",
            extra={
                "task_id": task_id,
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "event_type": event_type,
            },
        )

    def log_failure(
        self,
        *,
        task_id,
        tenant_id,
        user_id,
        event_type,
        exc,
    ):
        logger.exception(
            "notification_task_failed",
            extra={
                "task_id": task_id,
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "event_type": event_type,
                "exception_type": type(exc).__name__,
            },
        )

@shared_task(
    bind=True,
    base=NotificationTask,
    name="apps.notifications.tasks.process_notification",
)
def process_notification(
    self,
    *,
    tenant_id,
    user_id,
    event_type,
    title,
    message,
    resource_type="",
    resource_id=None,
    metadata=None,
):
    
    self.log_start(
        task_id=self.request.id,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
    )
    
    try:
        notification = NotificationService.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )
        self.log_success(
            task_id=self.request.id,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
        )
        
        if notification is None:
            return {
                "status": "skipped",
                "reason": "in_app_notifications_disabled",
            }
            
        return {
            "status": "created",
            "notification_id": str(notification.id),
            "event_type": notification.event_type,
        }
        
    except Exception as exc:
        self.log_failure(
            task_id=self.request.id,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            exc=exc,
        )
        raise


    