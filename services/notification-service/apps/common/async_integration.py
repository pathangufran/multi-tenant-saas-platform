from dataclasses import dataclass
from typing import Any
from celery import current_app

class AsyncIntegrationError(Exception):
    """Base exception for async integration failures."""


class UnsupportedEventError(AsyncIntegrationError):
    """Raised when an event has no registered async handler."""
    
@dataclass(frozen=True)
class AsyncEvent:
    event_id: str
    event_type: str
    tenant_id: str | None
    user_id: str | None
    payload: dict[str, Any]
    
class AsyncEventDispatcher:
    
    EVENT_TASKS = {
        "USER_INVITED": (
            "apps.notifications.tasks.process_notification"
        ),
        "TASK_ASSIGNED": (
            "apps.notifications.tasks.process_notification"
        ),
        "TASK_COMPLETED": (
            "apps.notifications.tasks.process_notification"
        ),
        "PASSWORD_RESET": (
            "apps.notifications.tasks.process_notification"
        ),
        "SUBSCRIPTION_CREATED": (
            "apps.notifications.tasks.process_notification"
        ),
        "PAYMENT_FAILED": (
            "apps.notifications.tasks.process_notification"
        ),
        "REPORT_READY": (
            "apps.notifications.tasks.process_notification"
        ),
    }

    @classmethod
    def get_task_name(
        cls,
        *,
        event_type: str,
    ) -> str:
        
        try:
            return cls.EVENT_TASKS[
                event_type
            ]
            
        except KeyError:
            raise UnsupportedEventError(
                f"No async handler registered "
                f"for event: {event_type}"
            )
            
    @classmethod
    def dispatch(
        cls,
        *,
        event: AsyncEvent,
    ):
        
        task_name = cls.get_task_name(
            event_type=event.event_type,
        )
        
        return current_app.send_task(
            task_name,
            kwargs={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "tenant_id": event.tenant_id,
                "user_id": event.user_id,
                "payload": event.payload,
            },
        )
        
class AsyncJobDispatcher:
    
    @staticmethod
    def dispatch_task(
        *,
        task_name: str,
        args: tuple | list | None = None,
        kwargs: dict | None = None,
        countdown: int | None = None,
    ):
        
        options = {}
        
        if countdown is not None:
            options["countdown"] = countdown
            
        return current_app.send_task(
            task_name,
            args=list(args or []),
            kwargs=kwargs or {},
            **options,
        )