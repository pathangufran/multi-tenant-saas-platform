from django.http import JsonResponse
from .health import check_database,check_redis

def health_check(request):
    return JsonResponse(
        {
            "status": "ok",
        }
    )

def readiness_check(request):
    database_ok = check_database()
    redis_ok = check_redis()

    checks = {
        "database": "ok" if database_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }

    ready = database_ok and redis_ok 

    return JsonResponse(
        {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
        },
        status=200 if ready else 503,
    )