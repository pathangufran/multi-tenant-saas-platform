from celery import shared_task
from apps.integrations.services import (
    BillingIntegrationService,
)

@shared_task(
    bind=True,
    name="apps.integrations.tasks.dispatch_billing_event",
    max_retries=3,
    default_retry_delay=30,
)
def dispatch_billing_event(self, event_id):
    try:
        return (
            BillingIntegrationService.dispatch_event(event_id),
        )
        
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(
    name="apps.integrations.tasks.dispatch_pending_billing_events",
)
def dispatch_pending_billing_events():
    return (
        BillingIntegrationService.
        dispatch_pending_events(limit=100)
    )