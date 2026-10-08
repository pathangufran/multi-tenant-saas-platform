import pytest
from unittest.mock import patch
from apps.common.integration_tasks import (
    dispatch_event,
)

class TestDispatchEventTask:

    @patch(
        "apps.common.integration_tasks.AsyncEventDispatcher.dispatch"
    )
    def test_dispatch_event_task(
        self,
        dispatch,
    ):

        celery_result = type(
            "CeleryResult",
            (),
            {
                "id": "celery-handler-123",
            },
        )()

        dispatch.return_value = (
            celery_result
        )

        result = dispatch_event.apply(
            kwargs={
                "event_id": "event-123",
                "event_type": "TASK_ASSIGNED",
                "tenant_id": "tenant-123",
                "user_id": "user-123",
                "payload": {
                    "task_id": "task-123",
                },
            }
        ).get()

        assert result == {
            "status": "dispatched",
            "event_id": "event-123",
            "event_type": "TASK_ASSIGNED",
            "task_id": "celery-handler-123",
        }

        dispatch.assert_called_once()

        event = (
            dispatch.call_args.kwargs["event"]
        )

        assert event.event_id == "event-123"

        assert (
            event.event_type
            == "TASK_ASSIGNED"
        )

        assert (
            event.tenant_id
            == "tenant-123"
        )

        assert (
            event.user_id
            == "user-123"
        )

        assert event.payload == {
            "task_id": "task-123",
        }