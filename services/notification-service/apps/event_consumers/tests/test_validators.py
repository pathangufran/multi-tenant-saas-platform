import uuid
from django.test import SimpleTestCase
from apps.event_consumers.exceptions import InvalidEventError
from apps.event_consumers.validators import validate_event_envelope

class EventEnvelopeValidatorTests(SimpleTestCase):

    def setUp(self):
        self.event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "task.assigned",
            "event_version": 1,
            "occurred_at": "2026-11-01T10:00:00+00:00",
            "producer": "core-service",
            "tenant_id": str(uuid.uuid4()),
            "aggregate_type": "task",
            "aggregate_id": str(uuid.uuid4()),
            "aggregate_version": 1,
            "correlation_id": str(uuid.uuid4()),
            "causation_id": None,
            "traceparent": None,
            "data": {
                "task_id": str(uuid.uuid4()),
            },
        }

    def test_valid_event_is_accepted(self):
        result = validate_event_envelope(self.event)

        self.assertEqual(result, self.event)

    def test_missing_field_is_rejected(self):
        event = self.event.copy()
        del event["event_id"]

        with self.assertRaises(InvalidEventError):
            validate_event_envelope(event)

    def test_invalid_event_id_is_rejected(self):
        event = self.event.copy()
        event["event_id"] = "invalid-uuid"

        with self.assertRaises(InvalidEventError):
            validate_event_envelope(event)

    def test_invalid_event_version_is_rejected(self):
        event = self.event.copy()
        event["event_version"] = 0

        with self.assertRaises(InvalidEventError):
            validate_event_envelope(event)

    def test_non_dictionary_data_is_rejected(self):
        event = self.event.copy()
        event["data"] = "invalid"

        with self.assertRaises(InvalidEventError):
            validate_event_envelope(event)

    def test_invalid_timestamp_is_rejected(self):
        event = self.event.copy()
        event["occurred_at"] = "not-a-timestamp"

        with self.assertRaises(InvalidEventError):
            validate_event_envelope(event)

    def test_non_dictionary_event_is_rejected(self):
        with self.assertRaises(InvalidEventError):
            validate_event_envelope([])