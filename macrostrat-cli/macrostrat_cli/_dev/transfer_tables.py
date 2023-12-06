import asyncio
from .utils import print_stream_progress, print_stdout
from sqlalchemy.engine import Engine
from .dump_database import _pg_dump
from .restore_database import _pg_restore


async def _transfer_tables(
    from_database: Engine,
    to_database: Engine,
    *,
    tables: list = [],
    schemas: list = [],
    dump_args: list = [],
    restore_args: list = [],
    **kwargs
):
    """Transfer tables from one database to another."""

    if len(tables) == 0 and len(schemas) == 0:
        raise ValueError("Must specify at least one table or schema to transfer")

    for schema in schemas:
        dump_args += ["--schema", schema]
    for table in tables:
        dump_args += ["--table", table]

    source = await _pg_dump(from_database, **kwargs, args=dump_args)
    dest = await _pg_restore(to_database, **kwargs, args=restore_args)

    await asyncio.gather(
        asyncio.create_task(print_stream_progress(source.stdout, dest.stdin)),
        asyncio.create_task(print_stdout(source.stderr)),
        asyncio.create_task(print_stdout(dest.stderr)),
    )
