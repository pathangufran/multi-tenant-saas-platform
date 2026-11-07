import logging
from celery import shared_task
from .publisher import OutboxPublisher

logger = logging.getLogger(__name__)

@shared_task(
    name="apps.outbox.tasks.publish_outbox_events",
)
def publish_outbox_events():
    
    result = OutboxPublisher.publish_batch(
        batch_size=100,
    )
    logger.info(
        "Auth outbox publishing completed: %s",
        result,
    )

    return result