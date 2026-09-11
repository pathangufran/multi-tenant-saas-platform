from rest_framework.response import Response
from rest_framework.views import exception_handler
from .error_response import build_error_response
from .exceptions import BaseApplicationException

def custom_exception_handler(exc,context):
    request = context.get("request")

    request_id = None

    if request is not None:
        request_id = getattr(
            request,"request_id",None
        )

    if isinstance(exc, BaseApplicationException):
        return __handle_application_exception(
            exc,
            request_id=request_id,
        )

    response = exception_handler(exc,context)

    if response is None:
        return None

    response.data = build_error_response(
        code="API_ERROR",
        message="An error occurred while processing the request.",
        request_id=request_id,
        details=response.data,
    )

    return response

def __handle_application_exception(
    exc: BaseApplicationException,
    *,
    request_id: str | None,
):
    return Response(
        build_error_response(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details,
        ),
        status=exc.status_code,
    )