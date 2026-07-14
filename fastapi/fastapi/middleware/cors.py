from starlette.middleware.cors import CORSMiddleware as CORSMiddleware  # noqa

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence

from starlette.middleware.cors import CORSMiddleware as _BaseCORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


class DynamicCORSMiddleware:
    """CORS middleware with dynamic origin validation via callback.

    Wraps Starlette's CORSMiddleware, evaluating an allow_origin_func callback
    on every request to determine whether the origin is permitted.
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Sequence[str] = (),
        allow_origin_func: Callable[[str], bool | Awaitable[bool]] | None = None,
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: str | None = None,
        expose_headers: Sequence[str] = (),
        cors_max_age: int = 600,
    ) -> None:
        self._allow_origins = allow_origins
        self._allow_origin_func = allow_origin_func
        self._cors_max_age = cors_max_age
        self._allow_methods = allow_methods
        self._allow_headers = allow_headers
        self._allow_credentials = allow_credentials
        self._allow_origin_regex = allow_origin_regex
        self._expose_headers = expose_headers

        self._inner: _BaseCORSMiddleware | None = None

    async def _resolve_allow_origins(self, origin: str) -> list[str]:
        """Evaluate the dynamic origin function and build the resolved allow list."""
        if self._allow_origin_func is not None:
            result = self._allow_origin_func(origin)
            if inspect.isawaitable(result):
                result = await result
            if result:
                return [origin]
            return []
        return list(self._allow_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Pass through non-HTTP scopes unchanged
            app = scope.get("app")
            if app is not None:
                await app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        # Determine the origin from headers
        origin = request.headers.get("origin", "")

        resolved_origins = await self._resolve_allow_origins(origin)

        # Build a fresh CORSMiddleware instance per request (shared state is minimal)
        middleware = _BaseCORSMiddleware(
            app=scope["app"],
            allow_origins=resolved_origins if not self._allow_origin_func else [origin] if resolved_origins else [],
            allow_methods=list(self._allow_methods),
            allow_headers=list(self._allow_headers),
            allow_credentials=self._allow_credentials,
            allow_origin_regex=self._allow_origin_regex,
            expose_headers=list(self._expose_headers),
            max_age=self._cors_max_age,
        )

        await middleware(scope, receive, send)
