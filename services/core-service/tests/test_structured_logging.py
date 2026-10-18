import json
import logging
from django.test import SimpleTestCase
from config.logging import JsonFormatter

class JsonFormatterTests(SimpleTestCase):
    def setUp(self):
        self.formatter = JsonFormatter(
            service_name="core-service",
            environment="test",
        )

    def make_record(self, message, level=logging.INFO, **extra):
        record = logging.LogRecord(
            name="apps.projects.services",
            level=level,
            pathname="services.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )

        for key, value in extra.items():
            setattr(record, key, value)

        return record

    def test_formats_log_as_valid_json(self):
        record = self.make_record("Project created")

        output = self.formatter.format(record)
        data = json.loads(output)

        self.assertEqual(data["message"], "Project created")
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["service"], "core-service")
        self.assertEqual(data["environment"], "test")
        self.assertEqual(data["logger"], "apps.projects.services")

    def test_includes_approved_extra_fields(self):
        record = self.make_record(
            "Project created",
            event="project.created",
            tenant_id="tenant-123",
            status_code=201,
            method="POST",
            path="/api/v1/projects/",
            duration_ms=24.5,
        )

        data = json.loads(self.formatter.format(record))

        self.assertEqual(data["event"], "project.created")
        self.assertEqual(data["tenant_id"], "tenant-123")
        self.assertEqual(data["status_code"], 201)
        self.assertEqual(data["method"], "POST")
        self.assertEqual(data["path"], "/api/v1/projects/")
        self.assertEqual(data["duration_ms"], 24.5)

    def test_excludes_unapproved_extra_fields(self):
        record = self.make_record(
            "Login completed",
            password="secret-password",
            access_token="secret-token",
            arbitrary_internal_value="do-not-log",
        )

        output = self.formatter.format(record)
        data = json.loads(output)

        self.assertNotIn("password", data)
        self.assertNotIn("access_token", data)
        self.assertNotIn("arbitrary_internal_value", data)
        self.assertNotIn("secret-password", output)
        self.assertNotIn("secret-token", output)

    def test_includes_exception_information(self):
        try:
            raise ValueError("Example failure")
        except ValueError:
            record = logging.LogRecord(
                name="apps.common.services",
                level=logging.ERROR,
                pathname="services.py",
                lineno=10,
                msg="Operation failed",
                args=(),
                exc_info=__import__("sys").exc_info(),
            )

        data = json.loads(self.formatter.format(record))

        self.assertEqual(data["level"], "ERROR")
        self.assertIn("ValueError", data["exception"])
        self.assertIn("Example failure", data["exception"])

    def test_timestamp_is_present_and_utc_aware(self):
        record = self.make_record("Health check completed")

        data = json.loads(self.formatter.format(record))

        self.assertIn("+00:00", data["timestamp"])

    def test_message_arguments_are_formatted(self):
        record = logging.LogRecord(
            name="apps.common.services",
            level=logging.INFO,
            pathname="services.py",
            lineno=15,
            msg="Processed %s records",
            args=(5,),
            exc_info=None,
        )

        data = json.loads(self.formatter.format(record))

        self.assertEqual(data["message"], "Processed 5 records")