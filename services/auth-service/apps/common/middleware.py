import uuid
from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

class RequestIDMiddleware:

    def __init__(self,get_response):
        self.get_response = get_response

    def __call__(self,request):
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.request_id = request_id
        token = request_id_context.set(request_id)
        
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id            
            return response
        finally:
            request_id_context.reset(token)
