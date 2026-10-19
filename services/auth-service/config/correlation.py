from config.request_context import get_request_id

def correlation_headers():
    
    request_id = get_request_id()
    
    if not request_id:
        return {}
    
    return {"X-Request-ID": request_id}