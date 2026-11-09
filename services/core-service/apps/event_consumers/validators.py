import uuid
from datetime import datetime,timezone
from apps.event_consumers.exceptions import (
    InvalidEventError,
)

class EventValidator:
    
    REQUIRED_FIELDS = {
        "event_id",
        "event_type",
        "event_version",
        "occurred_at",
        "producer",
        "tenant_id",
        "aggregate_type",
        "aggregate_id",
        "aggregate_version",
        "correlation_id",
        "causation_id",
        "traceparent",
        "data",
    }

    OPTIONAL_UUID_FIELDS = {
        "tenant_id",
        "causation_id",
    }

    UUID_FIELDS = {
        "event_id",
        "aggregate_id",
        "correlation_id",
    }

    STRING_FIELDS = {
        "event_type",
        "producer",
        "aggregate_type",
        "traceparent",
    }

    VERSION_FIELDS = {
        "event_version",
        "aggregate_version",
    }
    
    @classmethod
    def validate(cls,event):
        
        if not isinstance(event,dict):
            raise InvalidEventError(
                "Event must be a JSON object."
            )
            
        cls._validate_required_fields(event)
        cls._validate_uuid_fields(event)
        cls._validate_string_fields(event)
        cls._validate_versions(event)
        cls._validate_occurred_at(event)
        cls._validate_data(event)
        
        return event
    
    @classmethod
    def _validate_required_fields(cls,event):
        
        missing_fields = (
            cls.REQUIRED_FIELDS - event.keys()
        )
        if missing_fields:
            raise InvalidEventError(
                f"Missing required event fields: "
                f"{sorted(missing_fields)}"
            )
            
    @classmethod
    def _validate_uuid_fields(cls,event):
        
        for field in cls.UUID_FIELDS:
            value = event[field]
            
            try:
                uuid.UUID(str(value))
            
            except (ValueError,TypeError,AttributeError):
                raise InvalidEventError(
                    f"Invalid UUID field: {field}"
                )
                
        for field in cls.OPTIONAL_UUID_FIELDS:
            value = event[field]
            
            if value is None:
                continue
            
            try:
                uuid.UUID(str(value))
                
            except (ValueError,TypeError,AttributeError):
                raise InvalidEventError(
                    f"Invalid UUID field: {field}"
                )
                
    @classmethod
    def _validate_string_fields(cls,event):
        
        for field in cls.STRING_FIELDS:
            value = event[field]
            
            if not isinstance(value,str) or not value.strip():
                raise InvalidEventError(
                    f"Field '{field}' must be a non-empty string."
                )
                
    @classmethod
    def _validate_versions(cls,event):
        
        for field in cls.VERSION_FIELDS:
            value = event[field]
            
            if (
                isinstance(value,bool)
                or not isinstance(value,int)
                or value <= 0
            ):
                raise InvalidEventError(
                    f"Field '{field}' must be a positive integer."
                )
                
    @classmethod
    def _validate_occurred_at(cls,event):
        
        value = event["occurred_at"]
        
        if not isinstance(value,str) or not value.strip():
            raise InvalidEventError(
                "Field 'occurred_at' must be a non-empty ISO-8601 string."
            )
            
        try:
            parsed_datetime = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if parsed_datetime.tzinfo is None:
                raise ValueError(
                    "Timestamp must contain timezone information."
                )

            if parsed_datetime.utcoffset() is None:
                raise ValueError(
                    "Invalid timestamp timezone."
                )
                
        except (ValueError, TypeError):
            raise InvalidEventError(
                "Field 'occurred_at' must be a valid timezone-aware \
                ISO-8601 timestamp."
            )
            
    @classmethod
    def _validate_data(cls, event):

        if not isinstance(event["data"], dict):
            raise InvalidEventError(
                "Field 'data' must be a JSON object."
            )