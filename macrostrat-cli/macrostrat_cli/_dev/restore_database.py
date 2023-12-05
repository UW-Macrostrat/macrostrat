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


async def _pg_restore(
    dumpfile: Path,
    engine: Engine,
    database: str,
    *,
    create=False,
    pg_restore: Optional[list] = None,
    postgres_container: str = "postgres:15",
):
    # Pipe file to pg_restore, mimicking

    new_database = engine.url.set(database=database)

    db_exists = database_exists(new_database)
    if db_exists:
        print(f"Database [bold cyan]{new_database}[/] already exists")

    if create and not db_exists:
        console.print(f"Creating database [bold cyan]{new_database}[/]")
        create_database(new_database)

    # Run pg_restore in a local Docker container
    # TODO: this could also be run with pg_restore in a Kubernetes pod
    # or another location, if more appropriate. Running on the remote
    # host, if possible, is probably the fastest option. There should be
    # multiple options ideally.
    pg_restore = pg_restore or [
        "docker",
        "run",
        "-i",
        "--rm",
        "--network",
        "host",
        postgres_container,
        "pg_restore",
    ]

    proc = await asyncio.create_subprocess_exec(
        *pg_restore 
        "-d",
        str(new_database),
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        await asyncio.gather(
            asyncio.create_task(enqueue(source, proc.stdin)),
            asyncio.create_task(dequeue(proc.stderr)),
        )


async def enqueue(in_stream: asyncio.StreamReader, out_stream: asyncio.StreamWriter):
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


async def dequeue(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim")
