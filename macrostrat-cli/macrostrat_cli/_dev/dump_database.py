import asyncio
from typing import Optional
from sqlalchemy.engine import Engine
from pathlib import Path
import aiofiles
from .utils import _docker_local_run_args, print_stream_progress, print_stdout
from macrostrat.utils import get_logger

log = get_logger(__name__)


def pg_dump(*args, **kwargs):
    task = _pg_dump_to_file(*args, **kwargs)
    asyncio.run(task)


async def _pg_dump(
    engine: Engine,
    *,
    command_prefix: Optional[list] = None,
    args: list = [],
    postgres_container: str = "postgres:15",
    stdout=asyncio.subprocess.PIPE,
    verbose: bool = True,
):
    command_prefix = command_prefix or _docker_local_run_args(postgres_container)

    args_array = [*command_prefix, "pg_dump", "-Fc", str(engine.url), *args]

    if verbose:
        log.info(" ".join(args_array))
        print(" ".join(args_array))

    return await asyncio.create_subprocess_exec(
        *args_array,
        stdout=stdout,
        stderr=asyncio.subprocess.PIPE,
    )


async def _pg_dump_to_file(dumpfile: Path, engine: Engine, **kwargs):
    proc = await _pg_dump(engine, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="wb") as dest:
        await asyncio.gather(
            asyncio.create_task(print_stream_progress(proc.stdout, dest)),
            asyncio.create_task(print_stdout(proc.stderr)),
        )
