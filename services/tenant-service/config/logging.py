import json
import logging
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    """
    Format log records as structured JSON.

    Only explicitly approved extra fields are serialized.
    Request bodies, authorization headers, and arbitrary extras
    are deliberately excluded.
    """

    ALLOWED_EXTRA_FIELDS = (
        "event",
        "tenant_id",
        "request_id",
        "correlation_id",
        "status_code",
        "method",
        "path",
        "duration_ms",
        "task_id",
    )

    def __init__(
        self,
        service_name="unknown-service",
        environment="development",
    ):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record):
        timestamp = datetime.fromtimestamp(
            record.created,
            tz=timezone.utc,
        ).isoformat()

        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
        }

        for field in self.ALLOWED_EXTRA_FIELDS:
            value = getattr(record, field, None)

            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(
            payload,
            default=str,
            ensure_ascii=False,
        )