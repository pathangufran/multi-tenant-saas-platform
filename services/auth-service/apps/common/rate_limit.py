from django.core.cache import cache

class RateLimitExceeded(Exception):
    pass

class RateLimiter:

    @staticmethod
    def check(
        *,
        key: str,
        limit: int,
        window: int = 60,
    ) -> None:
        cache_key = f"rate-limit:{key}"

        client = cache._cache.get_client()
        current = client.incr(cache_key)

        if current == 1:
            client.expire(cache_key, window)

        if current > limit:
            raise RateLimitExceeded

    @staticmethod
    def get_client_ip(request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "unknown")
