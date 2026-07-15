import asyncio
from collections.abc import AsyncGenerator
from contextlib import AbstractContextManager
from contextlib import asynccontextmanager as asynccontextmanager
from typing import Any, TypeVar

import anyio.to_thread
from anyio import CapacityLimiter
from starlette.concurrency import iterate_in_threadpool as iterate_in_threadpool  # noqa
from starlette.concurrency import run_in_threadpool as run_in_threadpool  # noqa
from starlette.concurrency import (  # noqa
    run_until_first_complete as run_until_first_complete,
)

_T = TypeVar("_T")


@asynccontextmanager
async def contextmanager_in_threadpool(
    cm: AbstractContextManager[_T],
) -> AsyncGenerator[_T, None]:
    # blocking __exit__ from running waiting on a free thread
    # can create race conditions/deadlocks if the context manager itself
    # has its own internal pool (e.g. a database connection pool)
    # to avoid this we let __exit__ run without a capacity limit
    # since we're creating a new limiter for each call, any non-zero limit
    # works (1 is arbitrary)
    exit_limiter = CapacityLimiter(1)
    try:
        yield await run_in_threadpool(cm.__enter__)
    except Exception as e:
        ok = bool(
            await anyio.to_thread.run_sync(
                cm.__exit__, type(e), e, e.__traceback__, limiter=exit_limiter
            )
        )
        if not ok:
            raise e
    else:
        await anyio.to_thread.run_sync(
            cm.__exit__, None, None, None, limiter=exit_limiter
        )


class ConcurrencyError(Exception):
    """Raised when one or more coroutines in ``run_concurrently`` fail."""

    def __init__(self, errors: list[Exception]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} task(s) failed: {errors}")


async def run_concurrently(
    *coroutines: Any,
    max_concurrency: int = 10,
    timeout: float | None = None,
) -> list[Any]:
    """Run coroutines concurrently with a semaphore limit and optional timeout.

    Returns results in input order.  Raises ``ConcurrencyError`` if any task fails.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    errors: list[Exception] = []

    async def _run(idx: int, coro: Any) -> tuple[int, Any | Exception]:
        try:
            async with semaphore:
                result = await coro
            return idx, result
        except Exception as exc:
            return idx, exc

    tasks = [asyncio.create_task(_run(i, c)) for i, c in enumerate(coroutines)]

    async def _gather() -> list[tuple[int, Any | Exception]]:
        return list(await asyncio.gather(*tasks))

    try:
        if timeout is not None:
            results_raw = await asyncio.wait_for(_gather(), timeout=timeout)
        else:
            results_raw = await _gather()
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"run_concurrently timed out after {timeout}s"
        ) from None

    # Separate results and errors, preserving order
    results_sorted: list[Any] = [None] * len(coroutines)
    for idx, val in results_raw:
        if isinstance(val, Exception):
            errors.append(val)
        results_sorted[idx] = val

    if errors:
        raise ConcurrencyError(errors)

    return results_sorted
