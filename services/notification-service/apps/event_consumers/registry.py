
class EventHandlerRegistry:
    
    def __init__(self):
        self._handlers = {}
        
    def register(self,event_type,handler):
        if event_type in self._handlers:
            raise ValueError(
                f"Handler already registered for {event_type}"
            )
            
        if not callable(handler):
            raise TypeError("Handler must be callable.")
        
        self._handlers[event_type] = handler
        
    def get_handler(self,event_type):
        return self._handlers.get(event_type)
    
    def has_handler(self,event_type):
        return event_type in self._handlers
    
event_handler_registry = EventHandlerRegistry()