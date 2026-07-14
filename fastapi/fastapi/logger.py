import logging
from contextvars import ContextVar

logger = logging.getLogger("fastapi")

# Context variable for request ID, set by RequestIDMiddleware
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    """Logging filter that injects request_id from the context variable.

    When used with RequestIDMiddleware, this filter adds the request_id
    to every log record during the request's lifecycle.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
