import logging
from .middleware import request_id_context

class RequestIDFilter(logging.Filter):
    def filter(self,record):
        record.request_id = request_id_context.get()
        return True