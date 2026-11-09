from apps.event_consumers.exceptions import (
    EventHandlerAlreadyRegisteredError,
)

class EventHandlerRegistry:
    
    def __init__(self):
        self._handlers = {}
        
    def register(self,event_type,handler):
        
        if (
            not isinstance(event_type,str) or 
            not event_type.strip()
        ):
            raise ValueError(
                "Event type must be a non-empty string."
            )
        
        if not callable(handler):
            raise ValueError(
                "Event handler must be callable."
            )

        if event_type in self._handlers:
            raise EventHandlerAlreadyRegisteredError(
                f"Handler already registered for '{event_type}'."
            )
            
        self._handlers[event_type] = handler
        
    def get_handler(self,event_type):
        return self._handlers.get(event_type)
    
    def has_handler(self,event_type):
        return event_type in self._handlers

    def unregister(self, event_type):
        self._handlers.pop(event_type, None)

    def clear(self):
        self._handlers.clear()

    def registered_event_types(self):
        return tuple(self._handlers.keys())

event_handler_registry = EventHandlerRegistry()