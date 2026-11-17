from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase
from apps.common.cache.keys import CacheKeyBuilder
from apps.common.cache.service import CacheService
from apps.common.cache.policies import CacheTTL
from apps.common.cache.exceptions import CacheKeyError

class CacheKeyBuilderTests(SimpleTestCase):

    def test_builds_tenant_scoped_key(self):

        key = CacheKeyBuilder.build(
            resource="project",
            identifier="123",
            tenant_id="456",
        )

        self.assertEqual(
            key,
            "v1:project:tenant:456:123:v1",
        )

    def test_builds_global_key(self):

        key = CacheKeyBuilder.build(
            resource="plan",
            identifier="123",
        )

        self.assertEqual(
            key,
            "v1:plan:123:v1",
        )

    def test_rejects_empty_identifier(self):

        with self.assertRaises(CacheKeyError):

            CacheKeyBuilder.build(
                resource="project",
                identifier="",
            )

    def test_rejects_colon_in_identifier(self):

        with self.assertRaises(CacheKeyError):

            CacheKeyBuilder.build(
                resource="project",
                identifier="tenant:123",
            )

class CacheServiceTests(SimpleTestCase):

    def setUp(self):

        self.cache_service = CacheService()
        cache.clear()

    def tearDown(self):

        cache.clear()

    def test_set_and_get(self):

        self.cache_service.set(
            "test:key",
            {"name": "Project"},
            timeout=30,
        )

        result = self.cache_service.get("test:key")

        self.assertEqual(
            result,
            {"name": "Project"},
        )

    def test_returns_default_on_cache_miss(self):

        result = self.cache_service.get(
            "missing:key",
            default=None,
        )

        self.assertIsNone(result)

    def test_delete_removes_key(self):

        self.cache_service.set(
            "test:key",
            "value",
        )

        self.cache_service.delete("test:key")

        self.assertIsNone(
            self.cache_service.get("test:key")
        )

    def test_returns_default_when_redis_read_fails(self):

        with patch.object(
            self.cache_service.cache,
            "get",
            side_effect=ConnectionError("Redis unavailable"),
        ):

            result = self.cache_service.get(
                "test:key",
                default=None,
            )

        self.assertIsNone(result)

    def test_returns_false_when_redis_write_fails(self):

        with patch.object(
            self.cache_service.cache,
            "set",
            side_effect=ConnectionError("Redis unavailable"),
        ):

            result = self.cache_service.set(
                "test:key",
                "value",
            )

        self.assertFalse(result)

    def test_cache_ttl_policy(self):

        self.assertEqual(
            CacheTTL.MEDIUM.value,
            300,
        )