import asyncio
from rich.console import Console
from pathlib import Path
from sqlalchemy.engine import Engine
from sqlalchemy_utils import create_database, database_exists
import aiofiles
from typing import Optional
from .utils import _docker_local_run_args, print_stream_progress, print_stdout

console = Console()


def pg_restore(*args, **kwargs):
    task = _pg_restore_from_file(*args, **kwargs)
    asyncio.run(task)


async def _pg_restore(
    engine: Engine,
    *,
    create=False,
    command_prefix: Optional[list] = None,
    args: list = [],
    postgres_container: str = "postgres:15",
):
    # Pipe file to pg_restore, mimicking

    database = engine.url

    db_exists = database_exists(database)
    if db_exists:
        print(f"Database [bold cyan]{database}[/] already exists")

    if create and not db_exists:
        console.print(f"Creating database [bold cyan]{database}[/]")
        create_database(database)

    # Run pg_restore in a local Docker container
    # TODO: this could also be run with pg_restore in a Kubernetes pod
    # or another location, if more appropriate. Running on the remote
    # host, if possible, is probably the fastest option. There should be
    # multiple options ideally.
    command_prefix = command_prefix or _docker_local_run_args(postgres_container)

    return await asyncio.create_subprocess_exec(
        *command_prefix,
        "pg_restore",
        "-d",
        str(database),
        *args,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def _pg_restore_from_file(dumpfile: Path, *args, **kwargs):
    proc = await _pg_restore(*args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        await asyncio.gather(
            asyncio.create_task(print_stream_progress(source, proc.stdin)),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
