import asyncio
from docker.models.containers import Container
from typing import Optional
from sqlalchemy.engine import Engine
from pathlib import Path
import aiofiles
from .utils import _docker_local_run_args, print_stream_progress, print_stdout


async def _pg_dump(
    engine: Engine,
    *,
    command_prefix: Optional[list] = None,
    args: list = [],
    postgres_container: str = "postgres:15",
    user: Optional[str] = "postgres",
):
    command_prefix = command_prefix or _docker_local_run_args(postgres_container)

    _args = []
    if user is not None:
        _args += ["-U", user]
    _args += args

    return await asyncio.create_subprocess_exec(
        *command_prefix,
        "pg_dump",
        "-Fc",
        str(engine.url),
        *_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def _pg_dump_to_file(dumpfile: Path, *args, **kwargs):
    proc = await _pg_dump(*args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="wb") as dest:
        await asyncio.gather(
            asyncio.create_task(print_stream_progress(proc.stdout, dest)),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
