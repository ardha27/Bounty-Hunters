"""Server-Sent Events (SSE) support for FastAPI.

Adds disconnect detection, event filtering, reconnect replay, and SSEManager
for broadcasting to multiple clients.
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, AsyncGenerator, Callable, Optional

from annotated_doc import Doc
from fastapi.encoders import jsonable_encoder
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

# Default ping interval for SSE keep-alive (seconds)
_PING_INTERVAL: float = 15.0
# SSE comment used as keep-alive ping
KEEPALIVE_COMMENT = (
    '<EventSourceResponse> keep-alive ping</EventSourceResponse>'
)


def format_sse_event(event: "ServerSentEvent") -> str:
    """Format a ServerSentEvent for transmission."""
    return event.encode()


_SSE_EVENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "data": {"type": "string"},
        "event": {"type": "string"},
        "id": {"type": "string"},
        "retry": {"type": "integer"},
        "comment": {"type": "string"},
    },
}


class ServerSentEvent:
    """Represents an HTTP Server-Sent Event.

    See the W3C spec for details: https://html.spec.whatwg.org/multipage/server-sent-events.html
    """

    def __init__(
        self,
        data: Annotated[
            Any | None,
            Doc("The data field for the SSE message. Can be a dict or a string."),
        ] = None,
        *,
        event: Annotated[
            str | None,
            Doc(
                """Event type. Sent as `event:` field.

Allows clients using `EventSource.addEventListener()` to listen for named
events. **Must not contain newline characters.**"""
            ),
        ] = None,
        id: Annotated[
            str | None,
            Doc(
                """Event ID. Sent as `id:` field.

Allows clients to track the last event received for
automatic reconnection. **Must not contain null (`\\0`) characters.**"""
            ),
        ] = None,
        retry: Annotated[
            int | None,
            Doc(
                """Optional reconnection time in **milliseconds**.

Tells the browser how long to wait before reconnecting after the
connection is closed."""
            ),
        ] = None,
        comment: Annotated[
            str | None,
            Doc(
                """A comment field. Sent as a line starting with a colon.

Used as a keep-alive mechanism or for debugging."""
            ),
        ] = None,
        sep: Annotated[str | None, Doc("Event separator. Defaults to None.")] = None,
    ) -> None:
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment
        self.sep = sep

    def encode(self) -> str:
        """Encode the SSE message for transmission."""
        lines: list[str] = []
        if self.event is not None:
            lines.append(f"event: {self.event}")
        if self.data is not None:
            for chunk in json.dumps(self.data).split("\n"):
                lines.append(f"data: {chunk}")
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        if self.comment is not None:
            for line in str(self.comment).split("\n"):
                lines.append(f": {line}")
        return "\n".join(lines) + "\n\n"

    def __repr__(self) -> str:
        return f"ServerSentEvent(id={self.id!r}, event={self.event!r})"


class EventSourceResponse(StreamingResponse):
    """Streaming response for SSE endpoints with disconnect detection.

    Use as `response_class=EventSourceResponse` on a *path operation* that uses `yield`
    to produce `ServerSentEvent` instances.
    """

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str = "text/event-stream",
        background: BackgroundTask | None = None,
        ping_interval: Annotated[
            float | None,
            Doc(
                """Interval in seconds for keep-alive ping (comment) messages.

Sends an SSE comment periodically to detect client disconnection."""
            ),
        ] = 15.0,
        retry: Annotated[
            int | None,
            Doc(
                """Optional reconnection time in milliseconds (`retry:` field).

Sent at the start of the stream to tell clients how long to wait before
reconnecting."""
            ),
        ] = 3000,
    ) -> None:
        self._ping_interval = ping_interval
        self._retry = retry
        headers = headers or {}
        headers.setdefault("Cache-Control", "no-store")
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    async def stream_response(self, send: Send) -> None:
        """Override to detect client disconnect during streaming."""
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        try:
            async for data in self.body_iterator:
                if not isinstance(data, (bytes, memoryview)):
                    data = data.encode(self.charset)
                await send({"type": "http.response.body", "body": data, "more_body": True})
        except Exception:
            # Client likely disconnected — allow clean exit
            pass
        finally:
            await send({"type": "http.response.body", "body": b"", "more_body": False})


_SSE_CLIENT_ID_COUNTER = 0


class SSEManager:
    """Manages multiple SSE connections with broadcast and filtering capabilities."""

    def __init__(self) -> None:
        self._queues: dict[int, asyncio.Queue[ServerSentEvent | None]] = {}
        self._event_filters: dict[int, set[str] | None] = {}
        self._last_ids: dict[int, str | None] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        event_types: set[str] | None = None,
        last_event_id: str | None = None,
        replay_buffer: list[ServerSentEvent] | None = None,
    ) -> tuple[int, AsyncGenerator[ServerSentEvent, None]]:
        """Register a new SSE client.

        Returns a client ID and an async generator yielding events.
        Filters events by type if `event_types` is provided.
        If `last_event_id` is given, replays events from `replay_buffer` since that ID.
        """
        global _SSE_CLIENT_ID_COUNTER
        async with self._lock:
            _SSE_CLIENT_ID_COUNTER += 1
            client_id = _SSE_CLIENT_ID_COUNTER
            queue: asyncio.Queue[ServerSentEvent | None] = asyncio.Queue()
            self._queues[client_id] = queue
            self._event_filters[client_id] = event_types

        replay_from = False
        if last_event_id and replay_buffer:
            for evt in replay_buffer:
                if replay_from or evt.id == last_event_id:
                    replay_from = True
                    continue
                if replay_from and self._event_matches_filter(client_id, evt):
                    queue.put_nowait(evt)

        async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
            try:
                while True:
                    event = await queue.get()
                    if event is None:  # Disconnect signal
                        break
                    yield event
            except asyncio.CancelledError:
                pass

        return client_id, event_generator()

    def _event_matches_filter(self, client_id: int, event: ServerSentEvent) -> bool:
        """Check if an event matches the client's type filter."""
        filter_types = self._event_filters.get(client_id)
        if filter_types is None:
            return True
        return event.event in filter_types

    async def disconnect(self, client_id: int) -> None:
        """Remove a client connection."""
        async with self._lock:
            queue = self._queues.pop(client_id, None)
            self._event_filters.pop(client_id, None)
            if queue:
                await queue.put(None)  # Signal generator to stop

    async def broadcast(self, event: ServerSentEvent) -> None:
        """Send an event to all connected clients, respecting their filters."""
        async with self._lock:
            for client_id, queue in list(self._queues.items()):
                if self._event_matches_filter(client_id, event):
                    await queue.put(event)

    async def send(self, client_id: int, event: ServerSentEvent) -> None:
        """Send an event to a specific client."""
        async with self._lock:
            queue = self._queues.get(client_id)
            if queue and self._event_matches_filter(client_id, event):
                await queue.put(event)

    @property
    def client_count(self) -> int:
        """Return the number of connected clients."""
        return len(self._queues)
