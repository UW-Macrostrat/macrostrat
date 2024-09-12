import asyncio
from contextlib import contextmanager
from pathlib import Path
from sys import stdin
from tempfile import NamedTemporaryFile
from typing import Union

import aiofiles
from rich.console import Console
from sqlalchemy.engine import URL, Engine

from macrostrat.core.exc import MacrostratError
from macrostrat.database import database_exists
from macrostrat.utils import get_logger

from ..._dev.stream_utils import (
    DecodingStreamReader,
    print_stdout,
    print_stream_progress,
)
from ..._dev.utils import _create_command, _create_database_if_not_exists
from ..utils import docker_internal_url
from .utils import ParameterStyle, build_connection_args

console = Console()

log = get_logger(__name__)


def restore_mariadb(_input: Union[str, Path, None], engine: Engine, *args, **kwargs):
    """Restore a MariaDB database from a dump file or stream"""

    if _input is not None:
        if str(_input).startswith("http"):
            raise NotImplementedError("http(s) restore not yet implemented")

        _input = Path(_input)

    if _input is None:
        if stdin.isatty():
            raise MacrostratError("No input file specified")

        # Read from stdin
        _input = Path("/dev/stdin")

    if not _input.is_file() and not _input.is_fifo():
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
        # Stdout to dev null
        stdout=asyncio.subprocess.PIPE,
    )


async def _restore_mariadb_from_file(dumpfile: Path, engine: Engine, *args, **kwargs):
    proc = await _restore_mariadb(engine, *args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        s1 = DecodingStreamReader(source)
        await asyncio.gather(
            print_stream_progress(s1, proc.stdin, prefix="Restored"),
            print_stdout(proc.stderr),
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


def copy_mariadb_database(engine: Engine, new_engine: Engine, *args, **kwargs):
    """Copy a MariaDB database to a new database in the same cluster"""
    task = _copy_mariadb_database(engine, new_engine, *args, **kwargs)
    asyncio.run(task)


async def _copy_mariadb_database(engine: Engine, new_engine: Engine, *args, **kwargs):
    """Copy a MariaDB database to a new database in the same cluster"""
    container = kwargs.pop("container", "mariadb:10.10")

    overwrite = kwargs.pop("overwrite", False)
    create = kwargs.pop("create", True)
    if database_exists(new_engine.url) and not overwrite:
        console.print(
            f"Database [bold underline]{new_engine.url.database}[/] already exists. Use --overwrite to overwrite."
        )
        return

    dump = await _dump_mariadb(engine, *args, container=container)
    restore = await _restore_mariadb(
        new_engine, overwrite=overwrite, create=create, container=container
    )

    return await asyncio.gather(
        asyncio.create_task(
            print_stream_progress(dump.stdout, restore.stdin, prefix="Copied")
        ),
        asyncio.create_task(print_stdout(dump.stderr)),
        asyncio.create_task(print_stdout(restore.stderr)),
    )


@contextmanager
def _tempfile(suffix: str = ""):
    pth = Path("/tmp/sql-dump.sql")
    if pth.is_file():
        pth.unlink()
    yield pth
