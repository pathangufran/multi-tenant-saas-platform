from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase

class CacheConfigurationTests(SimpleTestCase):

    def test_default_cache_backend_is_redis(self):
        backend = settings.CACHES["default"]["BACKEND"]

        self.assertEqual(
            backend,
            "django.core.cache.backends.redis.RedisCache",
        )

    def test_cache_has_service_prefix(self):
        prefix = settings.CACHES["default"]["KEY_PREFIX"]

        self.assertTrue(prefix.startswith("saas:"))

    def test_cache_write_and_read(self):
        key = "configuration-test"
        value = {"status": "working"}

        cache.set(key, value, timeout=30)

        self.assertEqual(
            cache.get(key),
            value,
        )

        cache.delete(key)