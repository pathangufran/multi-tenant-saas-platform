from apps.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
)


def test_authentication_error():
    exc = AuthenticationError()

    assert exc.code == "AUTHENTICATION_ERROR"
    assert exc.status_code == 401


def test_authorization_error():
    exc = AuthorizationError()

    assert exc.code == "AUTHORIZATION_ERROR"
    assert exc.status_code == 403


def test_validation_error():
    exc = ValidationError()

    assert exc.code == "VALIDATION_ERROR"
    assert exc.status_code == 400


def test_resource_not_found_error():
    exc = ResourceNotFoundError()

    assert exc.code == "RESOURCE_NOT_FOUND"
    assert exc.status_code == 404


def test_conflict_error():
    exc = ConflictError()

    assert exc.code == "CONFLICT"
    assert exc.status_code == 409