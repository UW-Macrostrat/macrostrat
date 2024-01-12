import asyncio
from aiofiles.threadpool.binary import AsyncBufferedIOBase
from rich.console import Console
from sqlalchemy.engine import Engine
from macrostrat.utils import get_logger

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


def _create_command(
    engine: Engine,
    *command,
    args=[],
    prefix=None | list[str],
    container="postgres:16",
):
    command_prefix = prefix or _docker_local_run_args(container)
    _cmd = [*command_prefix, *command, str(engine.url), *args]

    log.info(" ".join(_cmd))

    # Replace asterisks with the real password (if any). This is kind of backwards
    # but it works.
    if "***" in str(engine.url) and engine.url.password is not None:
        _cmd = [
            *command_prefix,
            *command,
            str(engine.url).replace("***", engine.url.password),
            *args,
        ]

    return _cmd


async def print_stream_progress(
    in_stream: asyncio.StreamReader,
    out_stream: asyncio.StreamWriter | AsyncBufferedIOBase,
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
        else:
            out_stream.write(line)
            await out_stream.drain()
        i += 1
        if i == 1000:
            i = 0
            _print_progress(megabytes_written, end="\r")

    out_stream.close()
    _print_progress(megabytes_written)


def _print_progress(megabytes: float, **kwargs):
    progress = f"Dumped {megabytes:.1f} MB"
    print(progress, **kwargs)


async def print_stdout(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim")
