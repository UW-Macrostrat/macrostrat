import asyncio
from urllib.parse import quote

from aiofiles.threadpool.binary import AsyncBufferedIOBase
from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy_utils import create_database, database_exists, drop_database
from macrostrat.core.exc import MacrostratError


console = Console()

log = get_logger(__name__)


def _docker_local_run_args(postgres_container: str = "postgres:15"):
    return [
        "docker",
        "run",
        "-i",
        "--rm",
        "--network",
        "host",
        postgres_container,
    ]


def _create_database_if_not_exists(
    _url: URL, *, create=False, allow_exists=True, overwrite=False
):
    database = _url.database
    if overwrite:
        create = True
    db_exists = database_exists(_url)
    if db_exists:
        msg = f"Database [bold underline]{database}[/] already exists"
        if overwrite:
            console.print(f"{msg}, overwriting")
            drop_database(_url)
            db_exists = False
        elif not allow_exists:
            raise MacrostratError(msg, details="Use `--overwrite` to overwrite")
        else:
            console.print(msg)

    if create and not db_exists:
        console.print(f"Creating database [bold cyan]{database}[/]")
        create_database(_url)

    if not db_exists and not create:
        raise MacrostratError(
            f"Database [bold cyan]{database}[/] does not exist. "
            "Use `--create` to create it."
        )


def _create_command(
    *command,
    container=None | str,
):
    """Create a command for operating on a database"""

    _args = []
    if container is not None:
        _args = _docker_local_run_args(container)

    # We keep a separate list of arguments for logging purposes
    # in order to avoid logging the password in the URL
    _log_args = _args.copy()
    for arg in command:
        log_arg = arg
        if isinstance(arg, Engine):
            arg = arg.url
        if isinstance(arg, URL):
            log_arg = str(arg)
            arg = raw_database_url(arg)
        _log_args.append(log_arg)
        _args.append(arg)

    log.info(" ".join(_log_args))

    return _args


async def print_stream_progress(
    in_stream: asyncio.StreamReader,
    out_stream: asyncio.StreamWriter | AsyncBufferedIOBase | None,
):
    """This should be unified with print_stream_progress, but there seem to be
    slight API differences between aiofiles and asyncio.StreamWriter APIs.?"""
    megabytes_written = 0
    i = 0
    async for line in in_stream:
        megabytes_written += len(line) / 1_000_000
        if isinstance(out_stream, AsyncBufferedIOBase):
            await out_stream.write(line)
            await out_stream.flush()
        elif out_stream is not None:
            out_stream.write(line)
            await out_stream.drain()
        i += 1
        if i == 1000:
            i = 0
            _print_progress(megabytes_written, end="\r")

    if out_stream is not None:
        out_stream.close()
    _print_progress(megabytes_written)


def _print_progress(megabytes: float, **kwargs):
    progress = f"Dumped {megabytes:.1f} MB"
    print(progress, **kwargs)


async def print_stdout(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim")


def raw_database_url(url: URL):
    """Replace the password asterisks with the actual password, in order to pass to other commands."""
    _url = str(url)
    if "***" not in _url or url.password is None:
        return _url
    return _url.replace("***", quote(url.password, safe=""))
