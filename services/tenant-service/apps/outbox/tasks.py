import logging
from celery import shared_task
from .publisher import OutboxPublisher

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name="apps.outbox.tasks.publish_outbox_events",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
)
def publish_outbox_events(self):
    """
    Publish pending Tenant Service outbox events.

    Event-level Kafka failures are handled by OutboxPublisher.
    Infrastructure-level failures are retried by Celery.
    """
    
    stats = OutboxPublisher.publish_pending_events(
        batch_size=100,
    )
    logger.info(
        "Tenant outbox publishing completed: %s"
    )
    
    return stats