from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient
from apps.common.health_checks import HealthCheckService

class HealthCheckServiceTests(SimpleTestCase):
    @override_settings(SERVICE_NAME="billing-service")
    def test_liveness_returns_alive_status(self):
        result = HealthCheckService.liveness()

        self.assertEqual(result["status"], "alive")
        self.assertEqual(result["service"], "billing-service")
        self.assertIn("timestamp", result)

    @patch("apps.common.health_checks.connections")
    def test_database_check_executes_query(self, mock_connections):
        cursor = MagicMock()
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = cursor

        result = HealthCheckService._check_database()

        self.assertTrue(result)
        cursor.execute.assert_called_once_with("SELECT 1")
        cursor.fetchone.assert_called_once()

    @patch("apps.common.health_checks.redis.Redis.from_url")
    def test_redis_check_returns_true_when_ping_succeeds(self, mock_from_url):
        client = MagicMock()
        client.ping.return_value = True
        mock_from_url.return_value = client

        result = HealthCheckService._check_redis_url(
            "redis://localhost:6379/0"
        )

        self.assertTrue(result)
        client.ping.assert_called_once()
        client.close.assert_called_once()

    @patch("apps.common.health_checks.redis.Redis.from_url")
    def test_redis_check_returns_false_when_ping_is_false(
        self,
        mock_from_url,
    ):
        client = MagicMock()
        client.ping.return_value = False
        mock_from_url.return_value = client

        result = HealthCheckService._check_redis_url(
            "redis://localhost:6379/0"
        )

        self.assertFalse(result)
        client.close.assert_called_once()

    def test_redis_check_rejects_missing_or_invalid_url(self):
        self.assertFalse(HealthCheckService._check_redis_url(""))
        self.assertFalse(
            HealthCheckService._check_redis_url(
                "https://example.com"
            )
        )

    @patch.object(
        HealthCheckService,
        "_check_celery_broker",
        return_value=True,
    )
    @patch.object(
        HealthCheckService,
        "_check_redis",
        return_value=True,
    )
    @patch.object(
        HealthCheckService,
        "_check_database",
        return_value=True,
    )
    @override_settings(SERVICE_NAME="billing-service")
    def test_readiness_is_ready_when_all_dependencies_pass(
        self,
        mock_database,
        mock_redis,
        mock_broker,
    ):
        result = HealthCheckService.readiness()

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["service"], "billing-service")
        self.assertEqual(
            result["checks"],
            {
                "database": "ok",
                "redis": "ok",
                "celery_broker": "ok",
            },
        )

    @patch.object(
        HealthCheckService,
        "_check_celery_broker",
        return_value=True,
    )
    @patch.object(
        HealthCheckService,
        "_check_redis",
        side_effect=ConnectionError("internal connection details"),
    )
    @patch.object(
        HealthCheckService,
        "_check_database",
        return_value=True,
    )
    def test_readiness_fails_closed_on_dependency_exception(
        self,
        mock_database,
        mock_redis,
        mock_broker,
    ):
        result = HealthCheckService.readiness()

        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(result["checks"]["redis"], "unavailable")
        self.assertEqual(result["checks"]["database"], "ok")
        self.assertEqual(result["checks"]["celery_broker"], "ok")
        self.assertNotIn(
            "internal connection details",
            str(result),
        )

class HealthEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.common.views.HealthCheckService.liveness")
    def test_health_endpoint_returns_200(self, mock_liveness):
        mock_liveness.return_value = {
            "status": "alive",
            "service": "billing-service",
            "timestamp": "2026-10-19T10:00:00+00:00",
        }

        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "alive")

    @patch("apps.common.views.HealthCheckService.readiness")
    def test_ready_endpoint_returns_200_when_ready(self, mock_readiness):
        mock_readiness.return_value = {
            "status": "ready",
            "service": "billing-service",
            "timestamp": "2026-10-19T10:00:00+00:00",
            "checks": {
                "database": "ok",
                "redis": "ok",
                "celery_broker": "ok",
            },
        }

        response = self.client.get("/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ready")

    @patch("apps.common.views.HealthCheckService.readiness")
    def test_ready_endpoint_returns_503_when_not_ready(
        self,
        mock_readiness,
    ):
        mock_readiness.return_value = {
            "status": "not_ready",
            "service": "billing-service",
            "timestamp": "2026-10-19T10:00:00+00:00",
            "checks": {
                "database": "ok",
                "redis": "unavailable",
                "celery_broker": "ok",
            },
        }

        response = self.client.get("/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "not_ready")
