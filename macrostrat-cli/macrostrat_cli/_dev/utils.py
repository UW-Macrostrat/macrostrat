import asyncio
from rich.console import Console
from pathlib import Path
from sqlalchemy.engine import Engine
from sqlalchemy_utils import create_database, database_exists
import aiofiles
from typing import Optional

console = Console()


def pg_restore(*args, **kwargs):
    task = _pg_restore(*args, **kwargs)
    asyncio.run(task)


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


async def print_stream_progress(
    in_stream: asyncio.StreamReader, out_stream: asyncio.StreamWriter
):
    nbytes = 0
    i = 0
    progress = ""
    async for line in in_stream:
        nbytes += len(line)
        i += 1
        if i % 1000 == 0:
            _progress = nbytes / 1_000_000
            progress = f"Dumped {_progress:.1f} MB"
            print(progress, end="\r")
        out_stream.write(line)
        await out_stream.drain()
    out_stream.close()
    print(progress)


async def print_stdout(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim")
