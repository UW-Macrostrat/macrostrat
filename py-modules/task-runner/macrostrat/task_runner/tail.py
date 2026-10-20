"""Replay a run's output stream, then follow it until the run is over."""

from typing import AsyncIterator, Awaitable, Callable

from .output import _text, output_key

Entry = tuple[str, str]


async def tail_output(
    redis,
    run_id: str,
    *,
    since: str = "0-0",
    finished: Callable[[], Awaitable[bool]],
    block_ms: int = 15_000,
    count: int = 500,
) -> AsyncIterator[Entry | None]:
    """Yield `(entry_id, text)` from `since` onward; `None` when a block elapses
    with nothing new, so the caller can keep its connection alive.

    `finished` is consulted only after a quiet block: a run that is still
    producing output is plainly not over, and the ledger is the authority on
    when it is. A last non-blocking read drains what was written between the
    quiet block and the state change.
    """
    key = output_key(run_id)
    last = since
    while True:
        batches = await redis.xread({key: last}, block=block_ms, count=count)
        if batches:
            for _, entries in batches:
                for entry_id, fields in entries:
                    last = _text(entry_id)
                    yield last, _text(fields[b"d"])
            continue
        if await finished():
            batches = await redis.xread({key: last}, count=count)
            for _, entries in batches or []:
                for entry_id, fields in entries:
                    yield _text(entry_id), _text(fields[b"d"])
            return
        yield None
