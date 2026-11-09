
class InvalidEventError(Exception):
    """Raised when an incoming event violates the event contract."""

class EventHandlerAlreadyRegisteredError(Exception):
    """Raised when an event type is registered more than once."""

class EventHandlerNotFoundError(Exception):
    """Raised when no handler exists for an event type."""

class EventProcessingError(Exception):
    """Raised when event processing fails."""

    def __init__(self, message, event_id=None):
        self.event_id = event_id
        super().__init__(message)