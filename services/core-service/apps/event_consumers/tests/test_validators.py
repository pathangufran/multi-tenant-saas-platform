import uuid
from datetime import datetime, timezone
from django.test import SimpleTestCase
from apps.event_consumers.exceptions import InvalidEventError
from apps.event_consumers.validators import EventValidator

class EventValidatorTests(SimpleTestCase):

    def setUp(self):

        self.event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "project.created",
            "event_version": 1,
            "occurred_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "producer": "core-service",
            "tenant_id": str(uuid.uuid4()),
            "aggregate_type": "project",
            "aggregate_id": str(uuid.uuid4()),
            "aggregate_version": 1,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": "",
            "data": {
                "project_id": str(uuid.uuid4()),
                "name": "Test Project",
            },
        }

    def test_valid_event(self):

        result = EventValidator.validate(self.event)

        self.assertEqual(result, self.event)

    def test_non_dictionary_event(self):

        with self.assertRaises(InvalidEventError):
            EventValidator.validate([])

    def test_missing_required_field(self):

        event = self.event.copy()
        event.pop("event_id")

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_invalid_event_uuid(self):

        event = self.event.copy()
        event["event_id"] = "invalid-uuid"

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_invalid_aggregate_uuid(self):

        event = self.event.copy()
        event["aggregate_id"] = "invalid-uuid"

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_invalid_tenant_uuid(self):

        event = self.event.copy()
        event["tenant_id"] = "invalid-uuid"

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_null_tenant_id_is_allowed(self):

        event = self.event.copy()
        event["tenant_id"] = None

        self.assertEqual(
            EventValidator.validate(event),
            event,
        )

    def test_invalid_event_version(self):

        event = self.event.copy()
        event["event_version"] = 0

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_boolean_event_version_is_rejected(self):

        event = self.event.copy()
        event["event_version"] = True

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_invalid_aggregate_version(self):

        event = self.event.copy()
        event["aggregate_version"] = -1

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_invalid_occurred_at(self):

        event = self.event.copy()
        event["occurred_at"] = "invalid-date"

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_timezone_naive_timestamp_is_rejected(self):

        event = self.event.copy()
        event["occurred_at"] = "2026-11-07T12:00:00"

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_data_must_be_dictionary(self):

        event = self.event.copy()
        event["data"] = []

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)

    def test_empty_producer_is_rejected(self):

        event = self.event.copy()
        event["producer"] = ""

        with self.assertRaises(InvalidEventError):
            EventValidator.validate(event)