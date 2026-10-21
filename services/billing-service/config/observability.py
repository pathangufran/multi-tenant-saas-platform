import uuid
import sentry_sdk
from sentry_sdk.integrations.django import (
    DjangoIntegration,
)

def before_send(event, hint):
    request_data = event.get("request") or {}
    headers = request_data.get("headers") or {}

    request_id = None
    for name, value in headers.items():
        if name.lower() == "x-request-id":
            request_id = value
            break

    if request_id:
        try:
            request_id = str(uuid.UUID(request_id))
            
        except (ValueError, AttributeError, TypeError):
            request_id = None

    if request_id:
        event.setdefault(
            "tags", {}
        )["request_id"] = request_id

    return event

def initialize_error_tracking(
    *,
    dsn,
    environment,
    traces_sample_rate=0.0,
):
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[DjangoIntegration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        before_send=before_send,
    )
    
    return True
