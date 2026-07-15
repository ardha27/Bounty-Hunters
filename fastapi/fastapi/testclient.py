from base64 import b64encode
from contextlib import contextmanager
from typing import Any

from starlette.testclient import TestClient as _TestClient, WebSocketTestSession


class FastAPITestClient(_TestClient):
    """Extended TestClient with auth helpers and WebSocket convenience methods."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._auth_header: dict[str, str] | None = None

    def authenticate(self, token: str) -> None:
        """Set the Authorization Bearer token for all subsequent requests.

        Replaces any previously set token.
        """
        self._auth_header = {"Authorization": f"Bearer {token}"}

    def authenticate_basic(self, username: str, password: str) -> None:
        """Set HTTP Basic auth header for all subsequent requests.

        Base64 encodes the credentials.
        """
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        self._auth_header = {"Authorization": f"Basic {credentials}"}

    def reset_auth(self) -> None:
        """Clear the authentication state."""
        self._auth_header = None

    @contextmanager
    def ws_connect(
        self,
        url: str,
        subprotocols: list[str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Open a WebSocket connection with custom headers.

        Merges auth headers when set.
        """
        merged_headers: dict[str, str] = {}
        if self._auth_header:
            merged_headers.update(self._auth_header)
        if headers:
            merged_headers.update(headers)
        with self.websocket_connect(url, subprotocols=subprotocols, headers=merged_headers) as session:
            yield session

    def assert_status(self, method: str, url: str, expected: int, **kwargs: Any) -> Any:
        """Make a request and assert the response status code.

        Raises AssertionError with expected vs actual status on mismatch.
        """
        response = self.request(method, url, **kwargs)
        if response.status_code != expected:
            raise AssertionError(
                f"Expected status {expected}, got {response.status_code}"
            )
        return response

    def _merge_auth_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Merge stored auth headers with extra headers."""
        headers: dict[str, str] = {}
        if self._auth_header:
            headers.update(self._auth_header)
        if extra:
            headers.update(extra)
        return headers

    def get(self, *args: Any, **kwargs: Any) -> Any:
        """GET request with automatic auth headers."""
        if self._auth_header and "headers" not in kwargs:
            kwargs["headers"] = self._merge_auth_headers()
        elif self._auth_header and "headers" in kwargs:
            headers = self._merge_auth_headers(kwargs["headers"])
            kwargs["headers"] = headers
        return super().get(*args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> Any:
        """POST request with automatic auth headers."""
        if self._auth_header and "headers" not in kwargs:
            kwargs["headers"] = self._merge_auth_headers()
        elif self._auth_header and "headers" in kwargs:
            headers = self._merge_auth_headers(kwargs.get("headers"))
            kwargs["headers"] = headers
        return super().post(*args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> Any:
        """PUT request with automatic auth headers."""
        if self._auth_header and "headers" not in kwargs:
            kwargs["headers"] = self._merge_auth_headers()
        elif self._auth_header and "headers" in kwargs:
            headers = self._merge_auth_headers(kwargs.get("headers"))
            kwargs["headers"] = headers
        return super().put(*args, **kwargs)

    def patch(self, *args: Any, **kwargs: Any) -> Any:
        """PATCH request with automatic auth headers."""
        if self._auth_header and "headers" not in kwargs:
            kwargs["headers"] = self._merge_auth_headers()
        elif self._auth_header and "headers" in kwargs:
            headers = self._merge_auth_headers(kwargs.get("headers"))
            kwargs["headers"] = headers
        return super().patch(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """DELETE request with automatic auth headers."""
        if self._auth_header and "headers" not in kwargs:
            kwargs["headers"] = self._merge_auth_headers()
        elif self._auth_header and "headers" in kwargs:
            headers = self._merge_auth_headers(kwargs.get("headers"))
            kwargs["headers"] = headers
        return super().delete(*args, **kwargs)


TestClient = _TestClient  # noqa: F811 — keep backward compatibility
