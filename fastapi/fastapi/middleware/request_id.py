import uuid

from fastapi.logger import request_id_var
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique request ID to each incoming HTTP request.

    If the client sends an ``X-Request-ID`` header, that value is used and
    echoed back.  Otherwise a new UUID4 is generated.

    The request ID is stored in ``request.state.request_id`` and is injected
    into the ``request_id_var`` context variable so that the logger automatically
    includes it.  The ``X-Request-ID`` response header echoes the ID back.
    Concurrent requests are isolated — each request carries its own ID.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(
            "X-Request-ID", str(uuid.uuid4())
        )
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
