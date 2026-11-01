import uuid
import logging
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from config.correlation import correlation_headers
from config.middleware import RequestIDMiddleware
from config.request_context import (
    RequestContextFilter,
    get_request_id,
    resolve_request_id,
    reset_request_id,
    set_request_id,
)

class RequestIDResolutionTests(SimpleTestCase):
    def test_valid_uuid_is_normalized(self):
        supplied_id = str(uuid.uuid4()).upper()

        self.assertEqual(
            resolve_request_id(supplied_id),
            supplied_id.lower(),
        )

    def test_invalid_request_id_generates_uuid(self):
        request_id = resolve_request_id("invalid-header-value")

        self.assertEqual(str(uuid.UUID(request_id)), request_id)

    def test_missing_request_id_generates_uuid(self):
        request_id = resolve_request_id(None)

        self.assertEqual(str(uuid.UUID(request_id)), request_id)

class RequestIDMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_generates_request_id_and_adds_response_header(self):
        middleware = RequestIDMiddleware(
            lambda request: HttpResponse("ok")
        )
        request = self.factory.get("/health/")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(request, "request_id"))
        self.assertEqual(
            response["X-Request-ID"],
            request.request_id,
        )
        self.assertEqual(
            str(uuid.UUID(request.request_id)),
            request.request_id,
        )

    def test_preserves_valid_incoming_request_id(self):
        supplied_id = str(uuid.uuid4())
        middleware = RequestIDMiddleware(
            lambda request: HttpResponse("ok")
        )
        request = self.factory.get(
            "/health/",
            HTTP_X_REQUEST_ID=supplied_id,
        )

        response = middleware(request)

        self.assertEqual(request.request_id, supplied_id)
        self.assertEqual(response["X-Request-ID"], supplied_id)

    def test_replaces_invalid_incoming_request_id(self):
        middleware = RequestIDMiddleware(
            lambda request: HttpResponse("ok")
        )
        request = self.factory.get(
            "/health/",
            HTTP_X_REQUEST_ID="invalid\nforged-value",
        )

        response = middleware(request)

        self.assertNotEqual(
            response["X-Request-ID"],
            "invalid\nforged-value",
        )
        self.assertEqual(
            str(uuid.UUID(response["X-Request-ID"])),
            response["X-Request-ID"],
        )

    def test_request_context_is_reset_after_response(self):
        middleware = RequestIDMiddleware(
            lambda request: HttpResponse("ok")
        )
        request = self.factory.get("/health/")

        middleware(request)

        self.assertIsNone(get_request_id())

    def test_request_context_is_reset_after_exception(self):
        def failing_view(request):
            raise RuntimeError("Expected test exception")

        middleware = RequestIDMiddleware(failing_view)
        request = self.factory.get("/health/")

        with self.assertRaises(RuntimeError):
            middleware(request)

        self.assertIsNone(get_request_id())

class RequestContextFilterTests(SimpleTestCase):
    def test_filter_attaches_current_request_id(self):
        request_id = str(uuid.uuid4())
        token = set_request_id(request_id)

        try:
            record = logging.LogRecord(
                name="apps.common.services",
                level=logging.INFO,
                pathname="services.py",
                lineno=10,
                msg="Request processed",
                args=(),
                exc_info=None,
            )

            RequestContextFilter().filter(record)

            self.assertEqual(record.request_id, request_id)
        finally:
            reset_request_id(token)

    def test_filter_does_not_overwrite_existing_request_id(self):
        request_id = str(uuid.uuid4())
        token = set_request_id(str(uuid.uuid4()))

        try:
            record = logging.LogRecord(
                name="apps.common.services",
                level=logging.INFO,
                pathname="services.py",
                lineno=10,
                msg="Request processed",
                args=(),
                exc_info=None,
            )
            record.request_id = request_id

            RequestContextFilter().filter(record)

            self.assertEqual(record.request_id, request_id)
        finally:
            reset_request_id(token)

class CorrelationHeadersTests(SimpleTestCase):
    def test_returns_current_request_id_header(self):
        request_id = str(uuid.uuid4())
        token = set_request_id(request_id)

        try:
            self.assertEqual(
                correlation_headers(),
                {"X-Request-ID": request_id},
            )
        finally:
            reset_request_id(token)

    def test_returns_empty_headers_without_request_context(self):
        self.assertEqual(correlation_headers(), {})
