import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from fastapi.logger import request_id_var


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request ID to each request.

    Reads X-Request-ID from incoming request headers if present,
    otherwise generates a new UUID. The request ID is stored in
    request.state.request_id and echoed back in the X-Request-ID
    response header. Also sets a context variable for use by
    log filters (RequestIDFilter).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        request_id_var.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
