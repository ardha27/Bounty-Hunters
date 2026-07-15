from starlette.websockets import WebSocket as WebSocket  # noqa
from starlette.websockets import WebSocketDisconnect as WebSocketDisconnect  # noqa
from starlette.websockets import WebSocketState as WebSocketState  # noqa

import asyncio
import time
from collections.abc import Callable
from typing import Awaitable


class WebSocketWithHeartbeat:
    """
    WebSocket wrapper with configurable heartbeat/ping mechanism.

    Sends ping frames at a configurable interval. Closes the connection
    with code 1001 if no pong is received within the pong timeout.

    Parameters
    ----------
    websocket : WebSocket
        The underlying WebSocket connection.
    ping_interval : float
        Seconds between ping frames (default: 30).
    pong_timeout : float
        Seconds to wait for pong before closing (default: 10).
    on_disconnect : Callable[[int, float], Awaitable[None]] | None
        Optional async callback invoked on disconnect. Receives the
        close code and connection duration in seconds.
    """

    def __init__(
        self,
        websocket: WebSocket,
        *,
        ping_interval: float = 30.0,
        pong_timeout: float = 10.0,
        on_disconnect: Callable[[int, float], Awaitable[None]] | None = None,
    ):
        self._ws = websocket
        self._ping_interval = ping_interval
        self._pong_timeout = pong_timeout
        self._on_disconnect = on_disconnect
        self._start_time: float | None = None
        self._message_count: int = 0
        self._heartbeat_task: asyncio.Task | None = None
        self._closed = False

    @property
    def connection_duration(self) -> float | None:
        """Elapsed seconds since connection was opened, or None if not started."""
        if self._start_time is None:
            return None
        return time.monotonic() - self._start_time

    @property
    def message_count(self) -> int:
        """Number of messages received."""
        return self._message_count

    async def accept(self, subprotocol: str | None = None, headers: list[tuple[bytes, bytes]] | None = None) -> None:
        """Accept the WebSocket connection and start heartbeat."""
        await self._ws.accept(subprotocol=subprotocol, headers=headers)
        self._start_time = time.monotonic()
        self._heartbeat_task = asyncio.ensure_future(self._run_heartbeat())

    async def _run_heartbeat(self) -> None:
        """Send periodic pings and watch for pong responses."""
        try:
            while not self._closed:
                await asyncio.sleep(self._ping_interval)
                if self._closed:
                    break
                try:
                    await self._ws.send_ping()
                except Exception:
                    break

                # Wait for pong
                try:
                    await asyncio.wait_for(self._ws.receive_pong(), timeout=self._pong_timeout)
                except (asyncio.TimeoutError, Exception):
                    if not self._closed:
                        self._closed = True
                        await self._ws.close(code=1001, reason="Heartbeat pong timeout")
                        if self._on_disconnect and self.connection_duration is not None:
                            await self._on_disconnect(1001, self.connection_duration)
                    break
        except Exception:
            if not self._closed:
                self._closed = True
                if self._on_disconnect and self.connection_duration is not None:
                    await self._on_disconnect(1001, self.connection_duration)

    async def receive_text(self) -> str:
        """Receive a text message, counting it."""
        msg = await self._ws.receive_text()
        self._message_count += 1
        return msg

    async def receive_json(self, mode: str = "text") -> dict:
        """Receive a JSON message, counting it."""
        msg = await self._ws.receive_json(mode=mode)
        self._message_count += 1
        return msg

    async def receive_bytes(self) -> bytes:
        """Receive a bytes message, counting it."""
        msg = await self._ws.receive_bytes()
        self._message_count += 1
        return msg

    async def send_text(self, data: str) -> None:
        """Send a text message."""
        await self._ws.send_text(data)

    async def send_bytes(self, data: bytes) -> None:
        """Send bytes data."""
        await self._ws.send_bytes(data)

    async def send_json(self, data: dict, mode: str = "text") -> None:
        """Send JSON data."""
        await self._ws.send_json(data, mode=mode)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        """Close the WebSocket connection."""
        if self._closed:
            return
        self._closed = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        try:
            await self._ws.close(code=code, reason=reason)
        except Exception:
            pass
        if self._on_disconnect and self.connection_duration is not None:
            await self._on_disconnect(code, self.connection_duration)

    @property
    def client(self) -> WebSocket.client:
        return self._ws.client

    @property
    def application_state(self) -> WebSocket.application_state:
        return self._ws.application_state

    @property
    def state(self) -> WebSocketState:
        return self._ws.state

    @property
    def url(self) -> WebSocket.url:
        return self._ws.url

    @property
    def base_url(self) -> WebSocket.base_url:
        return self._ws.base_url

    @property
    def headers(self) -> WebSocket.headers:
        return self._ws.headers

    @property
    def query_params(self) -> WebSocket.query_params:
        return self._ws.query_params

    @property
    def path_params(self) -> WebSocket.path_params:
        return self._ws.path_params

    @property
    def cookies(self) -> WebSocket.cookies:
        return self._ws.cookies

    @property
    def client_state(self) -> WebSocket.client_state:
        return self._ws.client_state

    @property
    def scope(self) -> dict:
        return self._ws.scope

    async def __aenter__(self) -> "WebSocketWithHeartbeat":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
