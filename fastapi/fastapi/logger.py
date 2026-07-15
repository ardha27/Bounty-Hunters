import logging

from fastapi.middleware.request_id import request_id_var


class RequestIDFilter(logging.Filter):
    """Inject the current request ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"  # type: ignore[attr-defined]
        return True


logger = logging.getLogger("fastapi")
logger.addFilter(RequestIDFilter())
