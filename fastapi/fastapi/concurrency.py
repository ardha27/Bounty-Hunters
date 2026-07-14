import asyncio
from collections.abc import AsyncGenerator, Awaitable
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


class ConcurrencyError(Exception):
    """Raised when one or more concurrent tasks fail."""

    def __init__(self, errors: list[Exception]) -> None:
        self.errors = errors
        msg = f"{len(errors)} task(s) failed"
        super().__init__(msg)


async def run_concurrently(
    coros: list[Awaitable[_T]],
    *,
    max_concurrency: int = 10,
    timeout: float | None = None,
) -> list[_T]:
    """Run multiple coroutines concurrently with a semaphore limit.

    Args:
        coros: List of awaitables to execute.
        max_concurrency: Maximum number of concurrent tasks.
        timeout: Cancel remaining tasks after this many seconds.

    Returns:
        Results in the same order as the input coroutines.

    Raises:
        ConcurrencyError: If any task(s) fail, containing all exceptions.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    errors: list[Exception] = []
    results: list[_T | None] = [None] * len(coros)

    async def _wrapped(idx: int, coro: Awaitable[_T]) -> None:
        try:
            async with semaphore:
                result = await coro
                results[idx] = result
        except Exception as e:
            errors.append(e)
            results[idx] = None

    tasks = [asyncio.create_task(_wrapped(i, c)) for i, c in enumerate(coros)]

    try:
        if timeout is not None:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=False),
                timeout=timeout,
            )
        else:
            await asyncio.gather(*tasks, return_exceptions=False)
    except asyncio.TimeoutError:
        for t in tasks:
            t.cancel()
        errors.append(TimeoutError(f"run_concurrently timed out after {timeout}s"))
    except Exception as e:
        errors.append(e)

    if errors:
        raise ConcurrencyError(errors)

    return [_ for _ in results]  # type: ignore[return-value]


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
