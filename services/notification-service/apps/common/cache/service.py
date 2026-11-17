import logging
from django.core.cache import cache
from django.core.cache import caches
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ImproperlyConfigured
from apps.common.cache.exceptions import CacheSerializationError

logger = logging.getLogger(__name__)

class CacheService:

    def __init__(self, cache_alias="default"):

        self.cache = caches[cache_alias]

    def get(self, key, default=None):

        try:
            return self.cache.get(key, default)

        except Exception:
            logger.exception(
                "Cache read failed. Key: %s",
                key,
            )
            return default

    def set(self, key, value, timeout=300):

        try:
            return self.cache.set(
                key,
                value,
                timeout=timeout,
            )

        except Exception:
            logger.exception(
                "Cache write failed. Key: %s",
                key,
            )
            return False

    def delete(self, key):

        try:
            return self.cache.delete(key)

        except Exception:
            logger.exception(
                "Cache deletion failed. Key: %s",
                key,
            )
            return False

    def get_or_set(
        self,
        key,
        default,
        timeout=300,
    ):

        try:
            return self.cache.get_or_set(
                key,
                default,
                timeout=timeout,
            )

        except Exception:
            logger.exception(
                "Cache get_or_set failed. Key: %s",
                key,
            )

            if callable(default):
                return default()

            return default