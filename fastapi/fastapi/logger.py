import logging
import uuid
from contextvars import ContextVar

logger = logging.getLogger("fastapi")

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

def get_request_id() -> str:
    return request_id_var.get()

def set_request_id(request_id: str = "") -> str:
    if not request_id:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True
