import contextvars
import logging


class RequestIDLogFilter(logging.Filter):
    """
    Inject the current request ID into log records.

    Uses ``request_id_var`` — a :class:`contextvars.ContextVar` — so that
    the filter works correctly with async frameworks without leaking IDs
    between concurrent requests.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        rid = request_id_var.get(None)
        record.request_id = rid if rid is not None else "-"
        return True


#: Context variable that holds the request ID for the current request.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

logger = logging.getLogger("fastapi")
logger.addFilter(RequestIDLogFilter())
