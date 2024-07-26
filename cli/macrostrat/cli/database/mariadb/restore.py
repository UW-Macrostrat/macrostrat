import asyncio
from pathlib import Path
from typing import Optional
from sys import stdin

from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine
from macrostrat.core.exc import MacrostratError
import aiofiles

from .utils import build_connection_args
from macrostrat.core.config import docker_internal_url

from ..._dev.utils import (
    _create_command,
    _create_database_if_not_exists,
)
from ..._dev.stream_utils import print_stream_progress, print_stdout

console = Console()

log = get_logger(__name__)


def restore_mariadb(_input: Optional[str], engine: Engine, *args, **kwargs):
    """Restore a MariaDB database from a dump file or stream"""

    if _input.startswith("http"):
        raise NotImplementedError("HTTP(S) restore not yet implemented")

    if _input is not None:
        _input = Path(_input)

    if _input is None:
        if stdin.isatty():
            raise MacrostratError("No input file specified")

        # Read from stdin
        _input = Path("/dev/stdin")

    if not _input.is_file():
        raise MacrostratError(f"{_input} is not a file")

    task = _restore_mariadb_from_file(_input, engine, *args, **kwargs)
    asyncio.run(task)


async def _restore_mariadb(engine: Engine, *args, **kwargs):
    """Load MariaDB dump (GZipped SQL file) into a database."""
    overwrite = kwargs.pop("overwrite", False)
    create = kwargs.pop("create", overwrite)
    container = kwargs.pop("container", "mariadb:10.10")

    _create_database_if_not_exists(
        engine.url, create=create, allow_exists=False, overwrite=overwrite
    )
    conn = build_connection_args(docker_internal_url(engine.url))

    # Run pg_restore in a local Docker container
    # TODO: this could also be run with pg_restore in a Kubernetes pod
    # or another location, if more appropriate. Running on the remote
    # host, if possible, is probably the fastest option. There should be
    # multiple options ideally.
    _cmd = _create_command(
        "mariadb",
        *conn,
        *args,
        container=container,
    )

    log.debug(" ".join(_cmd))

    return await asyncio.create_subprocess_exec(
        *_cmd,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 1024 * 1,  # 1 MB windows
    )


async def _restore_mariadb_from_file(dumpfile: Path, engine: Engine, *args, **kwargs):
    proc = await _restore_mariadb(engine, *args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        s1 = DecodingStreamReader(source)
        await asyncio.gather(
            asyncio.create_task(
                print_stream_progress(s1, proc.stdin),
            ),
            asyncio.create_task(print_stdout(proc.stderr)),
        )

        # asyncio.create_task(print_stdout(proc.stderr)),



