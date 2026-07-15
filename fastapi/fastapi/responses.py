import importlib
from typing import Any, Protocol, cast

from fastapi.exceptions import FastAPIDeprecationWarning
from fastapi.sse import EventSourceResponse as EventSourceResponse  # noqa
from starlette.responses import FileResponse as FileResponse  # noqa
from starlette.responses import HTMLResponse as HTMLResponse  # noqa
from starlette.responses import JSONResponse as JSONResponse  # noqa
from starlette.responses import PlainTextResponse as PlainTextResponse  # noqa
from starlette.responses import RedirectResponse as RedirectResponse  # noqa
from starlette.responses import Response as Response  # noqa
from starlette.responses import StreamingResponse as StreamingResponse  # noqa
import csv
import io
from collections.abc import AsyncGenerator
from typing import Any, Literal

from starlette.types import Receive, Scope, Send

from typing_extensions import deprecated


class _UjsonModule(Protocol):
    def dumps(self, __obj: Any, *, ensure_ascii: bool = ...) -> str: ...


class _OrjsonModule(Protocol):
    OPT_NON_STR_KEYS: int
    OPT_SERIALIZE_NUMPY: int

    def dumps(self, __obj: Any, *, option: int = ...) -> bytes: ...


try:
    ujson = cast(_UjsonModule, importlib.import_module("ujson"))
except ModuleNotFoundError:  # pragma: nocover
    ujson = None  # type: ignore[assignment]


try:
    orjson = cast(_OrjsonModule, importlib.import_module("orjson"))
except ModuleNotFoundError:  # pragma: nocover
    orjson = None  # type: ignore[assignment]


@deprecated(
    "UJSONResponse is deprecated, FastAPI now serializes data directly to JSON "
    "bytes via Pydantic when a return type or response model is set, which is "
    "faster and doesn't need a custom response class. Read more in the FastAPI "
    "docs: https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model "
    "and https://fastapi.tiangolo.com/tutorial/response-model/",
    category=FastAPIDeprecationWarning,
    stacklevel=2,
)
class UJSONResponse(JSONResponse):
    """JSON response using the ujson library to serialize data to JSON.

    **Deprecated**: `UJSONResponse` is deprecated. FastAPI now serializes data
    directly to JSON bytes via Pydantic when a return type or response model is
    set, which is faster and doesn't need a custom response class.

    Read more in the
    [FastAPI docs for Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model)
    and the
    [FastAPI docs for Response Model](https://fastapi.tiangolo.com/tutorial/response-model/).

    **Note**: `ujson` is not included with FastAPI and must be installed
    separately, e.g. `pip install ujson`.
    """

    def render(self, content: Any) -> bytes:
        assert ujson is not None, "ujson must be installed to use UJSONResponse"
        return ujson.dumps(content, ensure_ascii=False).encode("utf-8")


@deprecated(
    "ORJSONResponse is deprecated, FastAPI now serializes data directly to JSON "
    "bytes via Pydantic when a return type or response model is set, which is "
    "faster and doesn't need a custom response class. Read more in the FastAPI "
    "docs: https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model "
    "and https://fastapi.tiangolo.com/tutorial/response-model/",
    category=FastAPIDeprecationWarning,
    stacklevel=2,
)
class ORJSONResponse(JSONResponse):
    """JSON response using the orjson library to serialize data to JSON.

    **Deprecated**: `ORJSONResponse` is deprecated. FastAPI now serializes data
    directly to JSON bytes via Pydantic when a return type or response model is
    set, which is faster and doesn't need a custom response class.

    Read more in the
    [FastAPI docs for Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model)
    and the
    [FastAPI docs for Response Model](https://fastapi.tiangolo.com/tutorial/response-model/).

    **Note**: `orjson` is not included with FastAPI and must be installed
    separately, e.g. `pip install orjson`.
    """

    def render(self, content: Any) -> bytes:
        assert orjson is not None, "orjson must be installed to use ORJSONResponse"
        return orjson.dumps(
            content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
        )


class StreamingCSVResponse(StreamingResponse):
    """Streaming CSV response for large dataset exports.

    Accepts an async generator of row data (lists or tuples).
    Sets Content-Type to text/csv and Content-Disposition to attachment.
    Handles RFC 4180 escaping of commas, quotes, and newlines.

    Args:
        content: Async generator yielding rows (list/tuple of values).
        headers: Optional column header names (first row output).
        filename: Filename for Content-Disposition header (default: 'export.csv').
        delimiter: CSV delimiter character (default: ',').
        media_type: Override the Content-Type (default: 'text/csv').
        status_code: HTTP status code (default: 200).
    """

    media_type = "text/csv"

    def __init__(
        self,
        content: AsyncGenerator[list[Any] | tuple[Any, ...], None],
        *,
        headers: list[str] | None = None,
        filename: str = "export.csv",
        delimiter: str = ",",
        status_code: int = 200,
    ) -> None:
        self._csv_headers = headers
        self._csv_filename = filename
        self._csv_delimiter = delimiter
        self._header_written = False

        super().__init__(
            content=self._csv_generator(content),
            status_code=status_code,
            media_type=self.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    async def _csv_generator(
        self,
        content: AsyncGenerator[list[Any] | tuple[Any, ...], None],
    ) -> AsyncGenerator[str, None]:
        """CSV encoding generator with RFC 4180 escaping."""
        output = io.StringIO()
        writer = csv.writer(
            output,
            delimiter=self._csv_delimiter,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )

        if self._csv_headers:
            writer.writerow(self._csv_headers)
            output.seek(0)
            yield output.read()
            output.seek(0)
            output.truncate(0)

        async for row in content:
            writer.writerow(row)
            output.seek(0)
            yield output.read()
            output.seek(0)
            output.truncate(0)
