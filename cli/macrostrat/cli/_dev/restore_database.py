import asyncio
from pathlib import Path

import aiofiles
from rich.console import Console
from sqlalchemy.engine import Engine

from macrostrat.utils import get_logger

from ..database.utils import docker_internal_url
from .stream_utils import print_stdout, print_stream_progress
from .utils import _create_command, _create_database_if_not_exists

console = Console()

log = get_logger(__name__)


def pg_restore(*args, **kwargs):
    task = _pg_restore_from_file(*args, **kwargs)
    asyncio.run(task)


async def _pg_restore(
    engine: Engine,
    *args,
    create=False,
    postgres_container: str = "postgres:15",
):
    # Pipe file to pg_restore, mimicking

    _create_database_if_not_exists(engine.url, create=create)

    # Run pg_restore in a local Docker container
    # TODO: this could also be run with pg_restore in a Kubernetes pod
    # or another location, if more appropriate. Running on the remote
    # host, if possible, is probably the fastest option. There should be
    # multiple options ideally.
    _cmd = _create_command(
        "pg_restore",
        "-d",
        docker_internal_url(engine.url),
        *args,
        container=postgres_container,
    )

    log.debug(" ".join(_cmd))

    return await asyncio.create_subprocess_exec(
        *_cmd,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 1024 * 1,  # 1 MB windows
    )


async def _pg_restore_from_file(dumpfile: Path, *args, **kwargs):
    proc = await _pg_restore(*args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        await asyncio.gather(
            asyncio.create_task(
                print_stream_progress(source, proc.stdin, prefix="Restored")
            ),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
