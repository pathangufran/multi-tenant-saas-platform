import json
import logging
import time
from django.conf import settings
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from kafka.structs import TopicPartition
from .services import EventProcessingService

logger = logging.getLogger(__name__)

class NotificationEventConsumer:
    
    def __init__(self):
        self.topic = settings.KAFKA_EVENTS_TOPIC
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = settings.KAFKA_CONSUMER_GROUP
        self.retry_delay = settings.KAFKA_CONSUMER_RETRY_DELAY
        
        self.consumer = None
        self.running = False
        
    def create_consumer(self):
        return KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers.split(","),
            group_id=self.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=1,
            value_deserializer=lambda value: json.loads(
                value.decode("utf-8")
            ),
            consumer_timeout_ms=1000,
        )
        
    def process_message(self,message):
        event = message.value
        
        result = EventProcessingService.process_event(
            event
        )
        logger.info(
            "Kafka event processed: event_id=%s event_type=%s status=%s",
            result["event_id"],
            event.get("event_type"),
            result["status"],
        )

        return result
    
    def commit_message(self):
        self.consumer.commit()
        
    def retry_message(self,message):
        partition = TopicPartition(
            message.topic,
            message.partition,
        )
        self.consumer.seek(
            partition,
            message.offset,
        )
        
        logger.exception(
            "Event processing failed. Retrying event at offset %s",
            message.offset,
        )

        time.sleep(self.retry_delay)

    def run(self):
        self.consumer = self.create_consumer()
        self.running = True
        
        logger.info(
            "Notification Kafka consumer started: topic=%s group=%s",
            self.topic,
            self.group_id,
        )
        
        try:
            while self.running:
                records = self.consumer.poll(
                    timeout_ms=1000,
                    max_records=1,
                )
                
                for _, messages in records.items():
                    for message in messages:
                        try:
                            self.process_message(message)
                            self.commit_message()
                        
                        except Exception:
                            self.retry_message(message)
                            
        except KeyboardInterrupt:
            logger.info(
                "Kafka consumer shutdown requested."
            )
        except KafkaError:
            logger.exception(
                "Kafka consumer encountered an error."
            )
        finally:
            self.close()
            
    def stop(self):
        self.running = False
        
    def close(self):
        if self.consumer is not None:
            self.consumer.close()
            self.consumer = None
            
        logger.info(
            "Notification Kafka consumer stopped."
        )
        
        
                        