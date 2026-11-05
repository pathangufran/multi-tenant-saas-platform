from celery import shared_task
from apps.outbox.publisher import (
    publish_pending_events,
)

@shared_task(
    bind=True,
    name="apps.outbox.tasks.publish_outbox_events",
    max_retries=3,
    default_retry_delay=10,
)
def publish_outbox_events(self):
    try:
        return publish_pending_events(
            limit=10
        )
        
    except Exception as exc:
        raise self.retry(
            exc=exc,
            countdown=10,
        )