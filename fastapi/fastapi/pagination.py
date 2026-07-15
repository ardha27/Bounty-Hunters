"""Standardized pagination with offset and cursor support."""
from base64 import b64decode, b64encode
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginatedResponse(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


@dataclass
class CursorPaginatedResponse(Generic[T]):
    items: list[T]
    next_cursor: str | None
    previous_cursor: str | None
    has_next: bool
    has_previous: bool


class Paginator:
    """Offset-based and cursor-based pagination helper.

    Usage as FastAPI dependency:
        @app.get("/items")
        def list_items(paginate: Paginator = Depends()):
            ...
    """

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100,
    ) -> None:
        self.page = max(1, page)
        self.page_size = max(1, min(page_size, max_page_size))
        self._max_page_size = max_page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    def paginate(self, items: list[T], total: int) -> PaginatedResponse[T]:
        """Wrap items in a PaginatedResponse."""
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        actual_page = min(self.page, total_pages) if total > 0 else 1
        return PaginatedResponse(
            items=items,
            total=total,
            page=actual_page,
            page_size=self.page_size,
            total_pages=total_pages,
            has_next=actual_page < total_pages,
            has_previous=actual_page > 1,
        )

    @staticmethod
    def encode_cursor(value: str) -> str:
        """Encode a value as a cursor string."""
        return b64encode(value.encode()).decode()

    @staticmethod
    def decode_cursor(cursor: str | None) -> str | None:
        """Decode a cursor string back to its original value."""
        if cursor is None:
            return None
        try:
            return b64decode(cursor.encode()).decode()
        except Exception:
            return None

    @staticmethod
    def cursor_paginate(
        items: list[T],
        cursor_field: str = "id",
        limit: int = 20,
        next_cursor: str | None = None,
    ) -> CursorPaginatedResponse[T]:
        """Wrap items in a CursorPaginatedResponse."""
        has_next = len(items) > limit
        trimmed = items[:limit]
        has_previous = next_cursor is not None
        if trimmed:
            last = trimmed[-1]
            last_val = getattr(last, cursor_field, str(last))
            new_next = Paginator.encode_cursor(str(last_val))
        else:
            new_next = None
        return CursorPaginatedResponse(
            items=trimmed,
            next_cursor=new_next if has_next else None,
            previous_cursor=next_cursor,
            has_next=has_next,
            has_previous=has_previous,
        )
