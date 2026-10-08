from celery import shared_task
from .async_integration import (
    AsyncEvent,
    AsyncEventDispatcher,
)

@shared_task(
    bind=True,
    name="apps.common.integration_tasks.dispatch_event",
)
def dispatch_event(
    self,
    event_id: str,
    event_type: str,
    tenant_id: str | None,
    user_id: str | None,
    payload: dict,
):
    """
    Dispatch a domain event to the appropriate
    asynchronous handler.
    """

    event = AsyncEvent(
        event_id=event_id,
        event_type=event_type,
        tenant_id=tenant_id,
        user_id=user_id,
        payload=payload,
    )
    result = AsyncEventDispatcher.dispatch(
        event=event,
    )

    return {
        "status": "dispatched",
        "event_id": event_id,
        "event_type": event_type,
        "task_id": result.id,
    }