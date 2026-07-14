import copy
import json

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.utils import is_body_allowed_for_status_code
from fastapi.websockets import WebSocket
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import WS_1008_POLICY_VIOLATION

_SENSITIVE_FIELDS = {"password", "secret", "token", "api_key"}


def _redact_sensitive(data: object) -> object:
    """Recursively redact sensitive fields from a dict or list."""
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if (isinstance(k, str) and k.lower() in _SENSITIVE_FIELDS)
            else _redact_sensitive(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_redact_sensitive(item) for item in data]
    return data


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    headers = getattr(exc, "headers", None)
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    return JSONResponse(
        {"detail": exc.detail}, status_code=exc.status_code, headers=headers
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    content: dict = {
        "detail": jsonable_encoder(exc.errors()),
        "path": request.url.path,
        "method": request.method,
    }

    # Read and echo request body in debug mode, with redaction
    # Check if we're in debug mode (FastAPI app debug flag)
    app = getattr(request.app, "debug", False)
    if app:
        try:
            body = exc.body
        except AttributeError:
            body = None
        if body is not None:
            try:
                body_data = json.loads(body) if isinstance(body, (str, bytes)) else body
            except (json.JSONDecodeError, TypeError):
                body_data = None

            content["body"] = _redact_sensitive(copy.deepcopy(body_data))

    return JSONResponse(status_code=422, content=content)


async def websocket_request_validation_exception_handler(
    websocket: WebSocket, exc: WebSocketRequestValidationError
) -> None:
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION, reason=jsonable_encoder(exc.errors())
    )
