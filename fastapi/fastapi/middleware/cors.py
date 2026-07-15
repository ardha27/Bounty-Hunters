from starlette.middleware.cors import CORSMiddleware as CORSMiddleware  # noqa

import inspect
from collections.abc import Sequence
from typing import Callable, Union

from starlette.middleware.cors import CORSMiddleware as _BaseCORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class DynamicCORSMiddleware(_BaseCORSMiddleware):
    """CORS middleware with dynamic origin validation callback and cors_max_age.

    Parameters match starlette.middleware.cors.CORSMiddleware plus:

    - **allow_origin_func**: Callable(origin: str) -> bool. Sync or async.
      Dynamically determines if an origin is allowed.
    - **cors_max_age**: int override for Access-Control-Max-Age preflight header.
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: str | None = None,
        allow_private_network: bool = False,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
        allow_origin_func: Callable[[str], object] | None = None,
        cors_max_age: int | None = None,
    ) -> None:
        if cors_max_age is not None:
            max_age = cors_max_age  # type: ignore[assignment]
        super().__init__(
            app=app,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
            allow_origin_regex=allow_origin_regex,
            allow_private_network=allow_private_network,
            expose_headers=expose_headers,
            max_age=max_age,
        )
        self._allow_origin_func = allow_origin_func
        self._cors_max_age = max_age

    async def _should_allow_origin(self, origin: str | None) -> bool:
        if origin is None:
            return False
        if self._allow_origin_func is not None:
            result = self._allow_origin_func(origin)
            if inspect.iscoroutine(result):
                result = await result  # type: ignore[assignment]
            return bool(result)
        if self.allow_all_origins:
            return True
        if self.allow_origin_regex is not None and self.allow_origin_regex.fullmatch(origin):
            return True
        return origin in self.allow_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        headers_list = scope.get("headers", [])
        headers = {k.decode(): v.decode() for k, v in headers_list}
        origin = headers.get("origin")

        if not await self._should_allow_origin(origin):
            await send({"type": "http.response.start", "status": 400, "headers": []})
            await send({"type": "http.response.body", "body": b""})
            return

        if method == "OPTIONS" and "access-control-request-method" in headers:
            response = self.preflight_response(request_headers=headers)
            if origin and self.preflight_explicit_allow_origin:
                response.headers["Access-Control-Allow-Origin"] = origin
            await response(scope, receive, send)
            return

        await self.simple_response(scope, receive, send, request_headers=headers)
