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


async def run_concurrently(
    *coroutines: Awaitable[_T],
    max_concurrency: int = 10,
) -> list[_T]:
    """
    Run multiple coroutines concurrently with a concurrency limit.

    Uses asyncio.Semaphore to bound the number of coroutines running
    simultaneously. Results are returned in the same order as input.

    Args:
        *coroutines: The awaitables to execute concurrently.
        max_concurrency: Maximum number of awaitables allowed to run at once.

    Returns:
        A list of results in the same order as the input coroutines.

    Raises:
        Any exception raised by an awaitable is propagated.
    """
    _asyncio = asyncio

    semaphore = _asyncio.Semaphore(max_concurrency)
    results: list[_T | None] = [None] * len(coroutines)

    async def _run(idx: int, coro: Awaitable[_T]) -> None:
        async with semaphore:
            results[idx] = await coro

    tasks = [
        _asyncio.create_task(_run(i, coro)) for i, coro in enumerate(coroutines)
    ]
    await _asyncio.gather(*tasks)
    return results  # type: ignore[return-value]


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
