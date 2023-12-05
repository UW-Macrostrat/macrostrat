import asyncio
from rich.console import Console
from pathlib import Path
from subprocess import run
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url, Engine
from sqlalchemy_utils import create_database, database_exists
import aiofiles

console = Console()


def pg_restore(*args, **kwargs):
    # loop = asyncio.get_event_loop()
    task = _pg_restore(*args, **kwargs)
    asyncio.run(task)
    # loop.run_until_complete(task)
    # loop.close()


async def _pg_restore(
    dumpfile: Path,
    engine: Engine,
    database: str,
    *,
    create=False,
    postgres_container: str = "postgres:15",
):
    # Pipe file to pg_restore, mimicking

    new_database = engine.url.set(database=database)
    print(new_database)

    db_exists = database_exists(new_database)
    if db_exists:
        print(f"Database {new_database} already exists")

    if create and not db_exists:
        print(f"Creating database {new_database}")
        create_database(new_database)

    print(dumpfile)

    # Read file bit by bit
    # source = await asyncio.create_subprocess_exec(
    #     "cat",
    #     str(dumpfile),
    #     stdout=asyncio.subprocess.PIPE,
    #     stderr=asyncio.subprocess.PIPE,
    # )  # TODO: there has to be a more pythonic way to do this

    # Use docker to run pg_restore
    run_args = [
        "docker",
        "run",
        "-i",
        "--rm",
        "--network",
        "host",
        postgres_container,
    ]

    proc = await asyncio.create_subprocess_exec(
        *run_args,
        "pg_restore",
        "-d",
        str(new_database),
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        await asyncio.gather(
            asyncio.create_task(enqueue(source, proc.stdin)),
            # # asyncio.create_task(dequeue(source.stderr)),
            # proc.wait(),
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
