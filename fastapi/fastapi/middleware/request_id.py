import uuid
from contextvars import ContextVar

from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns and tracks a unique request ID for log correlation.

    - Generates a UUID for each incoming request.
    - Echoes the client-provided ``X-Request-ID`` header if present.
    - Stores the request ID in ``request.state.request_id`` and a context variable.
    - Adds ``X-Request-ID`` to the response headers.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
