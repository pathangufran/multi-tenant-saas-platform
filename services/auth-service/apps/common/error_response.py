from typing import Any

def build_error_response(
    *,
    code: str,
    message: str,
    request_id: str | None = None,
    details: dict[str,Any] | None = None,
) -> dict[str,Any]:

    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        }
    }