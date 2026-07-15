from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable

from starlette.middleware.cors import CORSMiddleware as CORSMiddleware  # noqa: F401
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class DynamicCORSMiddleware:
    """CORS middleware with a dynamic origin-validation callback.

    Parameters
    ----------
    app :
        The ASGI application to wrap.
    allow_origin_func :
        Callable ``(origin: str) -> bool`` (sync or async).
    allow_origins :
        Static list of allowed origins (used when *allow_origin_func* is ``None``).
    allow_credentials : bool
        Passed through to the underlying ``CORSMiddleware``.
    allow_methods : list[str]
        Passed through.
    allow_headers : list[str]
        Passed through.
    expose_headers : list[str]
        Passed through.
    cors_max_age : int
        Seconds to cache preflight results (``Access-Control-Max-Age``).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        allow_origin_func: Callable[[str], bool | Awaitable[bool]] | None = None,
        allow_origins: list[str] | None = None,
        allow_credentials: bool = False,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        expose_headers: list[str] | None = None,
        cors_max_age: int = 600,
    ) -> None:
        self.app = app
        self._allow_origin_func = allow_origin_func
        self._allow_origins = allow_origins or ["*"]
        self._allow_credentials = allow_credentials
        self._allow_methods = allow_methods or ["GET"]
        self._allow_headers = allow_headers or []
        self._expose_headers = expose_headers or []
        self._cors_max_age = cors_max_age

        # Build static CORSMiddleware for the fallback path
        self._static_cors: CORSMiddleware | None = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        # Resolve origin
        origin = request.headers.get("origin")
        allowed = await self._is_origin_allowed(origin)

        if not allowed and origin:
            # Build a deny response
            response = Response(
                status_code=400,
                content=b"Origin not allowed",
                media_type="text/plain",
            )
            await response(scope, receive, send)
            return

        # Build temporary static middleware with the resolved origin
        resolved_origins = [origin] if (origin and allowed) else self._allow_origins
        cors = CORSMiddleware(
            app=self.app,
            allow_origins=resolved_origins,
            allow_credentials=self._allow_credentials,
            allow_methods=self._allow_methods,
            allow_headers=self._allow_headers,
            expose_headers=self._expose_headers,
            max_age=self._cors_max_age,
        )
        await cors(scope, receive, send)

    async def _is_origin_allowed(self, origin: str | None) -> bool:
        if not origin:
            return True  # non-browser requests pass through
        if self._allow_origin_func is not None:
            result = self._allow_origin_func(origin)
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        # Fallback to static list
        if "*" in self._allow_origins:
            return True
        return origin in self._allow_origins
