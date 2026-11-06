
class EventConsumerError(Exception):
    """Base exception for event consumer errors."""

class InvalidEventError(EventConsumerError):
    """Raised when an event does not match the expected envelope."""

class EventHandlerNotFoundError(EventConsumerError):
    """Raised when no handler is registered for an event type."""

class EventProcessingError(EventConsumerError):
    """Raised when event processing fails."""