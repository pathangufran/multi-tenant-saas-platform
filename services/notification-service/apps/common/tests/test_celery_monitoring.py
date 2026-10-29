from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient
from apps.common.celery_monitoring import CeleryMonitoringService

class CeleryWorkerStatusTests(SimpleTestCase):
    @patch("apps.common.celery_monitoring.current_app")
    def test_worker_status_available_when_worker_pongs(
        self,
        mock_app,
    ):
        inspector = MagicMock()
        inspector.ping.return_value = {
            "worker-1": {"ok": "pong"},
        }
        mock_app.control.inspect.return_value = inspector

        result = CeleryMonitoringService.worker_status()

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["workers"], ["worker-1"])

    @patch("apps.common.celery_monitoring.current_app")
    def test_worker_status_unavailable_when_no_workers(
        self,
        mock_app,
    ):
        inspector = MagicMock()
        inspector.ping.return_value = None
        mock_app.control.inspect.return_value = inspector

        result = CeleryMonitoringService.worker_status()

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["workers"], [])

    @patch("apps.common.celery_monitoring.current_app")
    def test_worker_status_handles_inspection_failure(
        self,
        mock_app,
    ):
        mock_app.control.inspect.side_effect = RuntimeError(
            "private broker details"
        )

        result = CeleryMonitoringService.worker_status()

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["workers"], [])
        self.assertNotIn("private broker details", str(result))

    @override_settings(CELERY_BROKER_URL="")
    def test_broker_status_unavailable_without_url(self):
        self.assertEqual(
            CeleryMonitoringService.broker_status(),
            {"status": "unavailable"},
        )

    @override_settings(CELERY_BROKER_URL="amqp://localhost")
    def test_broker_status_unsupported_for_other_transports(self):
        self.assertEqual(
            CeleryMonitoringService.broker_status(),
            {"status": "unsupported"},
        )

    @override_settings(CELERY_BROKER_URL="")
    def test_queue_depths_unavailable_without_broker_url(self):
        result = CeleryMonitoringService.queue_depths()

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["queues"], {})

    @override_settings(
        CELERY_BROKER_URL="redis://localhost:6379/5",
        CELERY_MONITORED_QUEUES=["celery", "notifications"],
    )
    @patch("apps.common.celery_monitoring.redis.Redis.from_url")
    def test_queue_depths_returns_configured_queue_counts(
        self,
        mock_from_url,
    ):
        client = MagicMock()
        client.llen.side_effect = [3, 7]
        mock_from_url.return_value = client

        result = CeleryMonitoringService.queue_depths()

        self.assertEqual(result["status"], "available")
        self.assertEqual(
            result["queues"],
            {"celery": 3, "notifications": 7},
        )
        self.assertEqual(client.llen.call_count, 2)
        client.close.assert_called_once()

    @patch.object(
        CeleryMonitoringService,
        "worker_status",
        return_value={
            "status": "available",
            "workers": ["worker-1"],
        },
    )
    @patch.object(
        CeleryMonitoringService,
        "broker_status",
        return_value={"status": "available"},
    )
    @patch.object(
        CeleryMonitoringService,
        "queue_depths",
        return_value={
            "status": "available",
            "queues": {"celery": 0},
        },
    )
    def test_overall_status_healthy_when_all_checks_pass(
        self,
        mock_queues,
        mock_broker,
        mock_workers,
    ):
        result = CeleryMonitoringService.get_status()

        self.assertEqual(result["status"], "healthy")

    @patch.object(
        CeleryMonitoringService,
        "worker_status",
        return_value={"status": "unavailable", "workers": []},
    )
    @patch.object(
        CeleryMonitoringService,
        "broker_status",
        return_value={"status": "available"},
    )
    @patch.object(
        CeleryMonitoringService,
        "queue_depths",
        return_value={
            "status": "available",
            "queues": {"celery": 0},
        },
    )
    def test_overall_status_degraded_when_workers_are_down(
        self,
        mock_queues,
        mock_broker,
        mock_workers,
    ):
        result = CeleryMonitoringService.get_status()

        self.assertEqual(result["status"], "degraded")

class CeleryMonitoringEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/admin/monitoring/celery/"

    def test_anonymous_user_cannot_access_monitoring(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])

    def test_non_staff_user_cannot_access_monitoring(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="monitoring-user",
            password="test-password",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    @patch(
        "apps.common.monitoring_views.CeleryMonitoringService.get_status"
    )
    def test_staff_user_can_access_monitoring(self, mock_status):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            username="monitoring-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_authenticate(user=admin)

        mock_status.return_value = {
            "status": "healthy",
            "broker": {"status": "available"},
            "workers": {
                "status": "available",
                "workers": ["worker-1"],
            },
            "queues": {
                "status": "available",
                "queues": {"celery": 0},
            },
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "healthy")
