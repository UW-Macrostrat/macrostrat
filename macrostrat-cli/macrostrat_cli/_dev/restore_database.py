import asyncio
from rich.console import Console


console = Console()


def pg_restore(source: str, target: str, database: str):
    loop = asyncio.get_event_loop()
    task = _pg_restore(source, target, database)
    loop.run_until_complete(task)
    loop.close()


async def _pg_restore(source: str, target: str, database: str):
    # Pipe file to pg_restore, mimicking

    source = await asyncio.create_subprocess_exec(
        "docker",
        "exec",
        "-i",
        "-u",
        "postgres",
        source.name,
        "pg_dump",
        "-Fc",
        "--superuser=postgres",
        "-U",
        "postgres",
        database,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    proc = await asyncio.create_subprocess_exec(
        "docker",
        "exec",
        "-i",
        "-u",
        "postgres",
        target.name,
        "pg_restore",
        "-U",
        "postgres",
        "-d",
        database,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.gather(
        asyncio.create_task(enqueue(source.stdout, proc.stdin)),
        asyncio.create_task(dequeue(source.stderr)),
        asyncio.create_task(dequeue(proc.stderr)),
    )


async def enqueue(in_stream: asyncio.StreamReader, out_stream: asyncio.StreamWriter):
    nbytes = 0
    i = 0
    async for line in in_stream:
        nbytes += len(line)
        i += 1
        if i % 100 == 0:
            print(f"Dumped {nbytes/1_000_000} MB        ", end="\r")
        out_stream.write(line)
        await out_stream.drain()
    out_stream.close()


async def dequeue(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim")
