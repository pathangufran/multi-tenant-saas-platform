import uuid
import contextvars
import logging

_request_id = contextvars.ContextVar(
    "request_id", default=None,
)

def get_request_id():
    return _request_id.get()

def set_request_id(request_id):
    return _request_id.set(request_id)

def reset_request_id(token):
    _request_id.reset(token)

class RequestContextFilter(logging.Filter):
    """Attach the current request ID to each 
    log record."""

    def filter(self, record):
        if not getattr(record, "request_id", None):
            request_id = get_request_id()
            if request_id:
                record.request_id = request_id

        return True

def resolve_request_id(candidate):
    """
    Reuse a valid UUID request ID; generate one otherwise.

    UUID validation prevents arbitrary header text from entering logs.
    """
    if candidate:
        try:
            return str(uuid.UUID(candidate))
        except (ValueError, AttributeError, TypeError):
            pass

    return str(uuid.uuid4())
