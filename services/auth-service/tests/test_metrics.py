from django.test import SimpleTestCase
from django.urls import reverse

class PrometheusMetricsEndpointTests(SimpleTestCase):
    def test_metrics_endpoint_returns_success(self):
        response = self.client.get("/metrics/")

        self.assertEqual(response.status_code, 200)

    def test_metrics_endpoint_returns_prometheus_text(self):
        response = self.client.get("/metrics/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "text/plain",
            response.headers.get("Content-Type", ""),
        )

        body = response.content.decode("utf-8")
        self.assertTrue(
            "# HELP" in body or "# TYPE" in body,
            "Expected Prometheus-formatted metrics.",
        )

    def test_metrics_endpoint_does_not_return_json(self):
        response = self.client.get("/metrics/")

        self.assertNotEqual(
            response.headers.get("Content-Type", "").split(";")[0],
            "application/json",
        )

    def test_metrics_endpoint_supports_get_only(self):
        response = self.client.post("/metrics/")

        self.assertIn(response.status_code, [405, 403])
