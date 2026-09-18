class BaseApplicationException(Exception):
    """Base exception for application-level errors."""

    default_code = "APPLICATION_ERROR"
    default_message = "An application error occurred."
    status_code = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict | None = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or dict()
        super().__init__(self.message)

class AuthenticationError(BaseApplicationException):
    default_code = "AUTHENTICATION_ERROR"
    default_message = "Authentication failed."
    status_code = 401

class AuthorizationError(BaseApplicationException):
    default_code = "AUTHORIZATION_ERROR"
    default_message = "Authorization failed."
    status_code = 403

class ValidationError(BaseApplicationException):
    default_code = "VALIDATION_ERROR"
    default_message = "Invalid request."
    status_code = 400

class ResourceNotFoundError(BaseApplicationException):
    default_code = "RESOURCE_NOT_FOUND"
    default_message = "The requested resource was not found."
    status_code = 404

class ConflictError(BaseApplicationException):
    default_code = "CONFLICT"
    default_message = "The requested operation conflicts with existing data."
    status_code = 409

class RateLimitError(BaseApplicationException):
    default_code = "RATE_LIMIT_EXCEEDED"
    default_message = "Too many requests."
    status_code = 429

class ExternalServiceError(BaseApplicationException):
    default_code = "EXTERNAL_SERVICE_ERROR"
    default_message = "An external service failed."
    status_code = 502

class DatabaseError(BaseApplicationException):
    default_code = "DATABASE_ERROR"
    default_message = "A database error occurred."
    status_code = 500

class ServiceUnavailableError(BaseApplicationException):
    default_code = "SERVICE_UNAVAILABLE"
    default_message = "The service is temporarily unavailable."
    status_code = 503
    
class RateLimitError(BaseApplicationException):
    status_code = 429
    default_code = "RATE_LIMIT_EXCEEDED"
    default_message = "Too many requests. Please try again later."