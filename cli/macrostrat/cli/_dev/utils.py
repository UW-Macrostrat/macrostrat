from urllib.parse import quote
import sys

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
        "--attach",
        "stdin",
        "--attach",
        "stdout",
        "--attach",
        "stderr",
        "--log-driver",
        "none",
        "--rm",
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

    for arg in command:
        if isinstance(arg, Engine):
            arg = arg.url
        if isinstance(arg, URL):
            arg = raw_database_url(arg)
        _args.append(arg)
    return _args


async def print_stream_progress(
    in_stream: asyncio.StreamReader,
    out_stream: asyncio.StreamWriter | AsyncBufferedIOBase,
    *,
    chunk_size: int = 64 * 1024,  # 64 KB
    prefix: str = "Dumped",
):
    """This should be unified with print_stream_progress, but there seem to be
    slight API differences between aiofiles and asyncio.StreamWriter APIs.?"""
    megabytes_written = 0
    while True:
        chunk = await in_stream.read(chunk_size)
        if not chunk:
            break
        megabytes_written += len(chunk) / 1_000_000
        if isinstance(out_stream, AsyncBufferedIOBase):
            await out_stream.write(chunk)
            await out_stream.flush()
        else:
            out_stream.write(chunk)
            await out_stream.drain()
        _print_progress(megabytes_written, end="\r")
    if hasattr(out_stream, "close"):
        out_stream.close()
    _print_progress(megabytes_written)


def _print_progress(megabytes: float, **kwargs):
    prefix = kwargs.get("prefix", "Dumped")
    progress = f"{prefix} {megabytes:.1f} MB"
    kwargs.setdefault("file", sys.stderr)
    print(progress, **kwargs)


async def print_stdout(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim", end="")


def raw_database_url(url: URL):
    """Replace the password asterisks with the actual password, in order to pass to other commands."""
    _url = str(url)
    if "***" not in _url or url.password is None:
        return _url
    return _url.replace("***", quote(url.password, safe=""))
