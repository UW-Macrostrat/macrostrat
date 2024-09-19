import asyncio
import sys
from pathlib import Path
from typing import Optional

import aiofiles
from macrostrat.utils import get_logger
from sqlalchemy.engine import Engine

from .stream_utils import print_stdout, print_stream_progress
from .utils import _create_command
from ..database.utils import docker_internal_url

log = get_logger(__name__)


def pg_dump(dumpfile: Path, *args, **kwargs):
    if dumpfile is None or dumpfile == sys.stdout:
        task = _pg_dump_to_stdout(*args, **kwargs)
    else:
        task = _pg_dump_to_file(dumpfile, *args, **kwargs)
    asyncio.run(task)


async def _pg_dump(
    engine: Engine,
    *args: str,
    postgres_container: str = "postgres:15",
    user: Optional[str] = "postgres",
    stdout=asyncio.subprocess.PIPE,
    custom_format: bool = True,
):
    _args = []
    if custom_format:
        _args.append("-Fc")

    if user is not None:
        _args += ["-U", user]
    _args += args

    _cmd = _create_command(
        "pg_dump",
        docker_internal_url(engine.url),
        *_args,
        container=postgres_container,
    )
    log.debug(" ".join(_cmd))
    return await asyncio.create_subprocess_exec(
        *_cmd,
        stdout=stdout,
        stderr=asyncio.subprocess.PIPE,
    )


async def _pg_dump_to_stdout(*args, **kwargs):
    proc = await _pg_dump(*args, **kwargs)
    await asyncio.gather(
        asyncio.create_task(print_stdout(proc.stdout)),
        asyncio.create_task(print_stream_progress(proc.stderr)),
    )


async def _pg_dump_to_file(dumpfile: Path, *args, **kwargs):
    proc = await _pg_dump(*args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="wb") as dest:
        await asyncio.gather(
            asyncio.create_task(
                print_stream_progress(proc.stdout, dest, prefix="Dumped")
            ),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
