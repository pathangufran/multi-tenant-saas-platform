import logging
from django.core.management.base import BaseCommand
from apps.event_consumers.consumer import (
    NotificationEventConsumer,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    
    help = "Start the Notification Service Kafka event consumer."
    
    def handle(self,*args,**options):
        consumer = NotificationEventConsumer()
        
        try:
            consumer.run()
        
        except Exception as exc:
            logger.exception(
                "Notification event consumer stopped unexpectedly."
            )
            raise exc