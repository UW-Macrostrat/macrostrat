import asyncio
from pathlib import Path
from typing import Optional
from sys import stdin

from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine, URL, create_engine
from macrostrat.core.exc import MacrostratError
import aiofiles

from .utils import build_connection_args, ParameterStyle
from macrostrat.core.config import docker_internal_url

from ..._dev.utils import (
    _create_command,
    _create_database_if_not_exists,
)
from ..._dev.stream_utils import (
    print_stream_progress,
    print_stdout,
    DecodingStreamReader,
)

console = Console()

log = get_logger(__name__)


def restore_mariadb(_input: Optional[str], engine: Engine, *args, **kwargs):
    """Restore a MariaDB database from a dump file or stream"""

    if _input.startswith("http"):
        raise NotImplementedError("http(s) restore not yet implemented")

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


def _log_command(url: URL, cmd: list[str]):
    logged_cmd = " ".join(cmd)
    if url.password:
        logged_cmd = logged_cmd.replace(url.password, "***")
    log.debug(logged_cmd)
    return logged_cmd


async def _restore_mariadb(engine: Engine, *args, **kwargs):
    """Load MariaDB dump (GZipped SQL file) into a database, using centrally managed credentials,
    a Docker containerized `mariadb` client, and a streaming approach."""
    overwrite = kwargs.pop("overwrite", False)
    create = kwargs.pop("create", overwrite)
    container = kwargs.pop("container", "mariadb:10.10")

    _create_database_if_not_exists(
        engine.url, create=create, allow_exists=False, overwrite=overwrite
    )
    conn = build_connection_args(docker_internal_url(engine.url))

    # Run mariadb in a local Docker container
    # or another location, if more appropriate. Running on the remote
    # host, if possible, is probably the fastest option. There should be
    # multiple options ideally.
    _cmd = _create_command(
        "mariadb",
        *conn,
        *args,
        container=container,
    )

    _log_command(engine.url, _cmd)

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


async def _dump_mariadb(engine: Engine, *args, **kwargs):
    """Dump a MariaDB database to a stream"""
    container = kwargs.pop("container", "mariadb:10.10")
    stdout = kwargs.pop("stdout", asyncio.subprocess.PIPE)

    conn = build_connection_args(
        docker_internal_url(engine.url), ParameterStyle.MySQLDump
    )

    _cmd = _create_command(
        "mysqldump",
        *conn,
        *args,
        container=container,
    )

    _log_command(engine.url, _cmd)

    return await asyncio.create_subprocess_exec(
        *_cmd,
        stdout=stdout,
        stderr=asyncio.subprocess.PIPE,
    )


def dump_mariadb(engine: Engine, dumpfile: Path, *args, **kwargs):
    task = _dump_mariadb_to_file(engine, dumpfile, *args, **kwargs)
    asyncio.run(task)


async def _dump_mariadb_to_file(engine: Engine, dumpfile: Path, *args, **kwargs):
    proc = await _dump_mariadb(engine, *args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="wb") as dest:
        await asyncio.gather(
            asyncio.create_task(print_stream_progress(proc.stdout, dest)),
            asyncio.create_task(print_stdout(proc.stderr)),
        )


def copy_mariadb_database(engine: Engine, new_database: str, *args, **kwargs):
    task = _copy_mariadb(engine, new_database, *args, **kwargs)
    asyncio.run(task)


async def _copy_mariadb(engine: Engine, new_database: str, *args, **kwargs):
    """Copy a MariaDB database to a new database in the same cluster"""
    new_url = engine.url.set(database=new_database)
    new_engine = create_engine(new_url)
    overwrite = kwargs.pop("overwrite", False)
    create = True

    dump = await _dump_mariadb(engine, *args, **kwargs)
    restore = await _restore_mariadb(
        new_engine, *args, **kwargs, create=create, overwrite=overwrite
    )

    # Connect the streams
    await asyncio.gather(
        asyncio.create_task(print_stream_progress(dump.stdout, restore.stdin)),
        asyncio.create_task(print_stdout(restore.stderr)),
    )
