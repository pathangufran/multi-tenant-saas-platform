import uuid
from unittest.mock import patch
from django.test import SimpleTestCase
from config.observability import (
    before_send,
    initialize_error_tracking,
)

class ErrorTrackingInitializationTests(SimpleTestCase):
    @patch("config.observability.sentry_sdk.init")
    def test_does_not_initialize_without_dsn(self, mock_init):
        result = initialize_error_tracking(
            dsn="",
            environment="test",
        )

        self.assertFalse(result)
        mock_init.assert_not_called()

    @patch("config.observability.sentry_sdk.init")
    def test_initializes_with_configured_dsn(self, mock_init):
        result = initialize_error_tracking(
            dsn="https://example.invalid/123",
            environment="test",
            traces_sample_rate=0.0,
        )

        self.assertTrue(result)
        mock_init.assert_called_once()

        kwargs = mock_init.call_args.kwargs
        self.assertEqual(
            kwargs["environment"],
            "test",
        )
        self.assertEqual(
            kwargs["traces_sample_rate"],
            0.0,
        )
        self.assertFalse(kwargs["send_default_pii"])
        self.assertIn("before_send", kwargs)

class BeforeSendTests(SimpleTestCase):
    def test_adds_valid_request_id_as_tag(self):
        request_id = str(uuid.uuid4())
        event = {
            "request": {
                "headers": {
                    "X-Request-ID": request_id,
                },
            },
        }

        result = before_send(event, {})

        self.assertEqual(
            result["tags"]["request_id"],
            request_id,
        )

    def test_normalizes_request_id(self):
        request_id = str(uuid.uuid4()).upper()
        event = {
            "request": {
                "headers": {
                    "x-request-id": request_id,
                },
            },
        }

        result = before_send(event, {})

        self.assertEqual(
            result["tags"]["request_id"],
            request_id.lower(),
        )

    def test_invalid_request_id_does_not_create_tag(self):
        event = {
            "request": {
                "headers": {
                    "X-Request-ID": "invalid-request-id",
                },
            },
        }

        result = before_send(event, {})

        self.assertNotIn(
            "request_id",
            result.get("tags", {}),
        )

    def test_missing_request_does_not_fail(self):
        event = {"message": "Background task failed"}

        result = before_send(event, {})

        self.assertEqual(result, event)

    def test_preserves_existing_event_tags(self):
        request_id = str(uuid.uuid4())
        event = {
            "tags": {"service": "billing-service"},
            "request": {
                "headers": {"X-Request-ID": request_id},
            },
        }

        result = before_send(event, {})

        self.assertEqual(
            result["tags"]["service"],
            "billing-service",
        )
        self.assertEqual(
            result["tags"]["request_id"],
            request_id,
        )
