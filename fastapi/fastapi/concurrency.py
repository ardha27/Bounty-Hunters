from collections.abc import AsyncGenerator, Awaitable, Coroutine
from contextlib import AbstractContextManager
from contextlib import asynccontextmanager as asynccontextmanager
from typing import TypeVar

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


import asyncio
from typing import Any


class ConcurrencyError(Exception):
    """Raised when one or more coroutines fail during concurrent execution."""

    def __init__(self, errors: list[tuple[int, Exception]]):
        self.errors = errors
        msg = "; ".join(f"Task {i}: {e!r}" for i, e in errors)
        super().__init__(f"{len(errors)} task(s) failed: {msg}")


class TimeoutError(RuntimeError):
    """Raised when concurrent execution exceeds the timeout."""


async def run_concurrently(
    coros: list[Coroutine[Any, Any, _T]],
    max_concurrency: int = 10,
    timeout: float | None = None,
) -> list[_T]:
    """Run coroutines concurrently with a semaphore-based concurrency limit.

    Args:
        coros: List of coroutines to execute.
        max_concurrency: Maximum number of coroutines to run simultaneously.
        timeout: Total time in seconds before cancelling remaining tasks.

    Returns:
        List of results in the same order as the input coroutines.

    Raises:
        ConcurrencyError: If one or more coroutines fail. Contains all errors.
        TimeoutError: If the timeout is exceeded.
    """
    if not coros:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(idx: int, coro: Coroutine[Any, Any, _T]) -> tuple[int, _T | None, Exception | None]:
        async with semaphore:
            try:
                result = await coro
                return (idx, result, None)
            except Exception as e:
                return (idx, None, e)

    tasks = {i: asyncio.create_task(_run(i, coro)) for i, coro in enumerate(coros)}

    try:
        done, pending = await asyncio.wait(tasks.values(), timeout=timeout)
    except Exception:
        for t in tasks.values():
            t.cancel()
        raise

    for t in pending:
        t.cancel()
    if pending:
        raise TimeoutError(
            f"Timeout after {timeout}s: {len(pending)} task(s) cancelled"
        )

    results: list[_T | None] = [None] * len(coros)
    errors: list[tuple[int, Exception]] = []
    for fut in tasks.values():
        idx, val, err = fut.result()
        if err is not None:
            errors.append((idx, err))
        else:
            results[idx] = val

    if errors:
        raise ConcurrencyError(errors)

    return results  # type: ignore[return-value]
