import redis
from datetime import datetime,timezone
from urllib.parse import urlparse
from django.conf import settings
from django.db import connections

class HealthCheckService:
    
    @staticmethod
    def liveness():
        return {
            "status": "alive",
            "service": settings.SERVICE_NAME,
            "timestamp": (
                datetime.now(timezone.utc)
                .isoformat(),
            )
        }
        
    @staticmethod
    def _check_database():
        connection = connections["default"]
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
        return True
    
    @classmethod
    def _check_redis_url(url):
        if not url:
            return False
        
        parsed = urlparse(url)
        if parsed.scheme not in ("redis","rediss"):
            return False
        
        client = redis.Redis.from_url(
            url,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry_on_timeout=False,
        )
        
        try:
            return bool(client.ping())
        finally:
            client.close()
            
    @classmethod
    def _check_redis(cls):
        return cls._check_redis_url(
            getattr(
                settings,"REDIS_URL",""
            )
        )
        
    @classmethod
    def _check_celery_broker(cls):
        return cls._check_redis_url(
            getattr(
                settings,"CELERY_BROKER_URL",""
            )
        )
        
    @classmethod
    def readiness(cls):
        checks = {}
        
        dependencies = {
            "database": cls._check_database,
            "redis": cls._check_redis,
            "celery_broker": cls._check_celery_broker,
        }
        
        for name,check in dependencies.items():
            try:
                checks[name] = (
                    "ok" if check() else "unavailable"
                )
            
            except Exception:
                checks[name] = "unavailable"
                
        ready = all(
            value == "ok" for value in checks.values()
        )

        return {
            "status": "ready" if ready else "not_ready",
            "service": settings.SERVICE_NAME,
            "timestamp": (
                datetime.now(timezone.utc)
                .isoformat(),
            ),
            "checks": checks,
        }

    