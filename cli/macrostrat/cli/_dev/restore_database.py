import asyncio
from pathlib import Path

import aiofiles
from macrostrat.database.transfer import pg_restore as _pg_restore
from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine

from .stream_utils import print_stdout, print_stream_progress

console = Console()

log = get_logger(__name__)


def pg_restore(dumpfile: Path, engine: Engine, **kwargs):
    task = _pg_restore_from_file(dumpfile, engine, **kwargs)
    asyncio.run(task)


async def _pg_restore_from_file(dumpfile: Path, engine: Engine, **kwargs):
    proc = await _pg_restore(engine, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        await asyncio.gather(
            asyncio.create_task(
                print_stream_progress(source, proc.stdin, prefix="Restored")
            ),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
