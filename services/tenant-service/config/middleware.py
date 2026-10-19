from config.request_context import (
    reset_request_id,
    resolve_request_id,
    set_request_id,
)

class RequestIDMiddleware:
    header_name = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied_id = request.META.get(
            self.header_name,
        )
        request_id = resolve_request_id(
            supplied_id,
        )
        token = set_request_id(request_id)
        request.request_id = request_id

        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(token)
