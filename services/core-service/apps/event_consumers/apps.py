from django.apps import AppConfig
from apps.event_consumers.handlers import (
    TenantLifecycleHandler,
)
from apps.event_consumers.registry import (
    event_handler_registry,
)

class EventConsumersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'event_consumers'
    verbose_name = 'Event Consumers'

    def ready(self):
        
        handlers = {
            "tenant.created": TenantLifecycleHandler.handle,
            "tenant.suspended": TenantLifecycleHandler.handle,
            "tenant.activated": TenantLifecycleHandler.handle,
            "tenant.deactivated": TenantLifecycleHandler.handle,
        }

        for event_type,handler in handlers.items():
            
            if not event_handler_registry.has_handler(event_type):
                event_handler_registry.register(
                    event_type,
                    handler,
                )