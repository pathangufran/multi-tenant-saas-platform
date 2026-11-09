
class InvalidEventError(Exception):
    """Raised when an incoming event violates the event contract."""


class EventHandlerAlreadyRegisteredError(Exception):
    """Raised when an event type is registered more than once."""


class EventHandlerNotFoundError(Exception):
    """Raised when no handler exists for an event type."""