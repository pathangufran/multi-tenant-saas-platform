import logging
import signal
import threading
from django.core.management.base import BaseCommand
from apps.event_consumers.consumer import (
    CoreEventConsumer,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    
    help = "Run the Core Service Kafka event consumer."
    
    def handle(self,*args,**options):
        
        consumer = CoreEventConsumer()
        shutdown_event = threading.Event()
        
        def shutdown_handler(signum,frame):
            
            if shutdown_event.is_set():
                return 
            
            logger.info(
                "Shutdown signal received.",
                extra={"signal": signum},
            )

            shutdown_event.set()
            consumer.stop()

        signal.signal(
            signal.SIGINT,
            shutdown_handler,
        )
        signal.signal(
            signal.SIGTERM,
            shutdown_handler,
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                "Starting Core Service Kafka consumer..."
            )
        )

        try:
            consumer.run()

        except Exception:
            logger.exception(
                "Core Service Kafka consumer terminated unexpectedly."
            )
            raise

        finally:
            consumer.close()

            self.stdout.write(
                self.style.WARNING(
                    "Core Service Kafka consumer stopped."
                )
            )