import json as _json
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.utils import is_body_allowed_for_status_code
from fastapi.websockets import WebSocket
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import WS_1008_POLICY_VIOLATION

_SENSITIVE_FIELDS = {"password", "secret", "token", "api_key"}


def _redact_sensitive(data: Any) -> Any:
    """Recursively redact sensitive field values from a dict/list."""
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if k.lower() in _SENSITIVE_FIELDS else _redact_sensitive(v)
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
    content: dict[str, Any] = {
        "detail": jsonable_encoder(exc.errors()),
        "path": request.url.path,
        "method": request.method,
    }
    debug = getattr(getattr(request, "app", None), "debug", False)
    if debug:
        try:
            body_bytes = await request.body()
            body = _json.loads(body_bytes) if body_bytes else None
            content["body"] = _redact_sensitive(body)
        except Exception:
            content["body"] = None
    return JSONResponse(status_code=422, content=content)


async def websocket_request_validation_exception_handler(
    websocket: WebSocket, exc: WebSocketRequestValidationError
) -> None:
    await websocket.close(
        code=WS_1008_POLICY_VIOLATION, reason=jsonable_encoder(exc.errors())
    )
