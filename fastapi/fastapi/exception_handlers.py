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


def _redact_body(body: dict) -> dict:
    """Recursively redact sensitive fields from a dict."""
    result = copy.deepcopy(body)
    for key, value in result.items():
        if key.lower() in _SENSITIVE_FIELDS or any(
            key.lower().endswith(f"_{sf}") or key.lower().startswith(f"{sf}_")
            for sf in _SENSITIVE_FIELDS
        ):
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = _redact_body(value)
        elif isinstance(value, list):
            result[key] = [
                _redact_body(item) if isinstance(item, dict) else item
                for item in value
            ]
    return result


async def _get_request_body(request: Request) -> dict | None:
    """Safely retrieve the request body if available."""
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return None
        decoded = body_bytes.decode("utf-8")
        return json.loads(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError, RuntimeError):
        return None


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

    is_debug = getattr(getattr(request, "app", None), "debug", False)
    if is_debug:
        body = await _get_request_body(request)
        if body is not None:
            content["body"] = _redact_body(body)

    return JSONResponse(status_code=422, content=content)


async def websocket_request_validation_exception_handler(
    websocket: WebSocket, exc: WebSocketRequestValidationError
) -> None:
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION, reason=jsonable_encoder(exc.errors())
    )
