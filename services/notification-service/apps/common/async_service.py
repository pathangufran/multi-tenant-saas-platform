import uuid
from typing import Any
from .async_integration import (
    AsyncEvent,
    AsyncEventDispatcher,
)
from .integration_tasks import dispatch_event

class AsyncIntegrationService:

    @staticmethod
    def create_event(
        *,
        event_type: str,
        tenant_id: str | None,
        user_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> AsyncEvent:

        return AsyncEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            tenant_id=(
                str(tenant_id)
                if tenant_id is not None
                else None
            ),
            user_id=(
                str(user_id)
                if user_id is not None
                else None
            ),
            payload=payload or {},
        )

    @staticmethod
    def dispatch_event(
        *,
        event_type: str,
        tenant_id: str | None,
        user_id: str | None,
        payload: dict[str, Any] | None = None,
    ):

        event = (
            AsyncIntegrationService.create_event(
                event_type=event_type,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=payload,
            )
        )

        AsyncEventDispatcher.get_task_name(
            event_type=event.event_type,
        )

        return dispatch_event.delay(
            event.event_id,
            event.event_type,
            event.tenant_id,
            event.user_id,
            event.payload,
        )
        
    @staticmethod
    def generate_report(
        *,
        tenant_id,
        report_type: str,
        requested_by=None,
    ):

        return AsyncIntegrationService.dispatch_task(
            task_name=(
                "apps.reports.tasks.generate_report"
            ),
            kwargs={
                "tenant_id": str(tenant_id),
                "report_type": report_type,
                "requested_by": (
                    str(requested_by)
                    if requested_by is not None
                    else None
                ),
            },
        )

    @staticmethod
    def generate_export(
        *,
        export_id,
    ):

        return AsyncIntegrationService.dispatch_task(
            task_name=(
                "apps.exports.tasks.generate_export"
            ),
            args=[
                str(export_id),
            ],
        )

    @staticmethod
    def dispatch_task(
        *,
        task_name: str,
        args=None,
        kwargs=None,
        countdown=None,
    ):

        from .async_integration import (
            AsyncJobDispatcher,
        )

        return AsyncJobDispatcher.dispatch_task(
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            countdown=countdown,
        )