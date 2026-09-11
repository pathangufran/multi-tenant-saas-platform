from django.core.cache import cache
from django.db import connection

def check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return True

    except Exception:
        return False

def check_redis() -> bool:
    try:
        cache.set("health_check","ok",timeout=10)
        return cache.get("health_check") == "ok"
    
    except Exception:
        return False