import copy
import json
import unittest
from pathlib import Path
from jsonschema import (
    Draft202012Validator, FormatChecker
)

BASE_DIR = Path(__file__).resolve().parents[1]

SCHEMA_PATH = BASE_DIR / "event.schema.json"
EXAMPLE_PATH = BASE_DIR / "event_examples.json"

class EventSchemaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with SCHEMA_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            cls.schema = json.load(file)

        with EXAMPLE_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            cls.valid_event = json.load(file)

        Draft202012Validator.check_schema(cls.schema)

        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )

    def test_schema_is_valid(self):
        Draft202012Validator.check_schema(
            self.schema
        )

    def test_example_event_is_valid(self):
        self.validator.validate(
            self.valid_event
        )

    def test_missing_event_id_is_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event.pop("event_id")

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_invalid_event_type_is_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event["event_type"] = "TASK_ASSIGNED"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_unknown_producer_is_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event["producer"] = "unknown-service"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_unsupported_event_version_is_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event["event_version"] = 2

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_invalid_tenant_uuid_is_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event["tenant_id"] = "invalid-tenant-id"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_platform_event_can_have_null_tenant(self):
        event = copy.deepcopy(self.valid_event)
        event["tenant_id"] = None

        self.validator.validate(event)

    def test_invalid_timestamp_is_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event["occurred_at"] = "not-a-timestamp"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_additional_envelope_fields_are_rejected(self):
        event = copy.deepcopy(self.valid_event)
        event["password"] = "should-not-be-here"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_data_must_be_an_object(self):
        event = copy.deepcopy(self.valid_event)
        event["data"] = "invalid-payload"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_traceparent_format(self):
        event = copy.deepcopy(self.valid_event)
        event["traceparent"] = "invalid-trace"

        errors = list(
            self.validator.iter_errors(event)
        )

        self.assertTrue(errors)

    def test_optional_traceparent_can_be_null(self):
        event = copy.deepcopy(self.valid_event)
        event["traceparent"] = None

        self.validator.validate(event)

    def test_extra_payload_fields_are_allowed(self):
        event = copy.deepcopy(self.valid_event)
        event["data"]["priority"] = "HIGH"

        self.validator.validate(event)

if __name__ == "__main__":
    unittest.main()
