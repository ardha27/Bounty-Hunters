from __future__ import annotations

import base64
from contextlib import contextmanager
from typing import Any, Generator, Sequence

from starlette.testclient import TestClient as _TestClient  # noqa: F401
from starlette.testclient import TestClient as TestClient  # noqa: F401
from starlette.testclient import WebSocketTestSession


class FastAPITestClient(_TestClient):
    """TestClient with auth helpers and WebSocket convenience methods."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-redef]
        super().__init__(*args, **kwargs)
        self._auth_headers: dict[str, str] = {}

    # ── auth helpers ───────────────────────────────────────────────

    def authenticate(self, token: str) -> None:
        """Set Bearer token for all subsequent requests."""
        self._auth_headers["Authorization"] = f"Bearer {token}"

    def authenticate_basic(self, username: str, password: str) -> None:
        """Set HTTP Basic auth header (base64-encoded)."""
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._auth_headers["Authorization"] = f"Basic {encoded}"

    def reset_auth(self) -> None:
        """Clear all auth headers."""
        self._auth_headers.clear()

    def _build_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Merge instance-level auth headers with per-request headers."""
        merged = dict(self._auth_headers)
        if headers:
            merged.update(headers)
        return merged

    # ── convenience methods ────────────────────────────────────────

    def assert_status(
        self,
        method: str,
        url: str,
        expected_status: int,
        **kwargs: Any,
    ) -> Any:
        """Make a request and assert the status code."""
        headers = self._build_headers(kwargs.pop("headers", None))
        response = self.request(method, url, headers=headers, **kwargs)
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got "
            f"{response.status_code} ({response.reason_phrase}) for "
            f"{method} {url}"
        )
        return response

    @contextmanager
    def ws_connect(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        subprotocols: Sequence[str] | None = None,
    ) -> Generator[WebSocketTestSession, None, None]:
        """WebSocket connection with custom headers and subprotocols."""
        client_headers: list[tuple[bytes, bytes]] = [
            (str(k).lower().encode(), str(v).encode())
            for k, v in (self._build_headers(headers) if headers else self._auth_headers).items()
        ]
        with self.websocket_connect(
            url, headers=client_headers, subprotocols=subprotocols
        ) as session:
            yield session
