import redis
from urllib.parse import urlparse
from celery import current_app
from django.conf import settings

class CeleryMonitoringService:
    
    @staticmethod
    def worker_status():
        """
        Check whether at least one Celery worker 
        responds to ping.
        Do not expose broker URLs or exception details
        in the result.
        """
        try:
            inspector = (
                current_app.control.inspect(
                    timeout=2
                )
            )
            responses = inspector.ping() or {}

            workers = sorted(
                worker_name
                for worker_name, response in responses.items()
                if response.get("ok") == "pong"
            )

            return {
                "status": (
                    "available" if workers else "unavailable"
                ),
                "workers": workers,
            }
            
        except Exception:
            return {
                "status": "unavailable",
                "workers": [],
            }

    @staticmethod
    def broker_status():
        """
        Check broker connectivity without returning
        connection details.
        """
        broker_url = getattr(
            settings, "CELERY_BROKER_URL", ""
        )
        if not broker_url:
            return {"status": "unavailable"}

        parsed = urlparse(broker_url)
        if parsed.scheme not in ("redis", "rediss"):
            return {"status": "unsupported"}

        client = None

        try:
            client = redis.Redis.from_url(
                broker_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
            )

            return {
                "status": (
                    "available" if client.ping() else "unavailable"
                )
            }
            
        except Exception:
            return {"status": "unavailable"}
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    @staticmethod
    def queue_depths():
        """
        Return Redis list lengths for explicitly configured queues.

        Configure CELERY_MONITORED_QUEUES as a list of queue names.
        For Redis's default Celery queue, the default is 'celery'.
        """
        broker_url = getattr(settings, "CELERY_BROKER_URL", "")
        queues = getattr(
            settings,
            "CELERY_MONITORED_QUEUES",
            ["celery"],
        )
        if not broker_url:
            return {
                "status": "unavailable",
                "queues": {},
            }

        parsed = urlparse(broker_url)
        if parsed.scheme not in ("redis", "rediss"):
            return {
                "status": "unsupported",
                "queues": {},
            }

        client = None

        try:
            client = redis.Redis.from_url(
                broker_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
            )
            depths = {
                queue: client.llen(queue)
                for queue in queues
            }

            return {
                "status": "available",
                "queues": depths,
            }
                
        except Exception:
            return {
                "status": "unavailable",
                "queues": {},
            }
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    @classmethod
    def get_status(cls):
        workers = cls.worker_status()
        broker = cls.broker_status()
        queues = cls.queue_depths()

        healthy = (
            workers["status"] == "available"
            and broker["status"] == "available"
            and queues["status"] == "available"
        )

        return {
            "status": (
                "healthy" if healthy else "degraded"
            ),
            "broker": broker,
            "workers": workers,
            "queues": queues,
        }
