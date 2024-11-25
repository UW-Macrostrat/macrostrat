import asyncio
import sys
from pathlib import Path

import aiofiles
from macrostrat.database.transfer import pg_dump as _pg_dump, pg_dump_to_file
from macrostrat.utils import get_logger
from sqlalchemy.engine import Engine

from .stream_utils import print_stdout, print_stream_progress

log = get_logger(__name__)


def pg_dump(dumpfile: Path, engine: Engine, **kwargs):
    if dumpfile is None or dumpfile == sys.stdout:
        task = _pg_dump_to_stdout(engine, **kwargs)
    else:
        task = pg_dump_to_file(engine, **kwargs)
    asyncio.run(task)


async def _pg_dump_to_stdout(engine: Engine, **kwargs):
    proc = await _pg_dump(engine, **kwargs)
    await asyncio.gather(
        asyncio.create_task(print_stdout(proc.stdout)),
        asyncio.create_task(print_stream_progress(proc.stderr)),
    )


async def _pg_dump_to_file(dumpfile: Path, engine: Engine, **kwargs):
    proc = await _pg_dump(engine, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="wb") as dest:
        await asyncio.gather(
            asyncio.create_task(
                print_stream_progress(proc.stdout, dest, prefix="Dumped")
            ),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
