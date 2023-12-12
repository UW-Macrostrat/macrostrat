import asyncio
from rich.console import Console

console = Console()


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
    megabytes_written = 0
    i = 0
    async for line in in_stream:
        megabytes_written += len(line) / 1_000_000
        out_stream.write(line)
        if hasattr(out_stream, "drain"):
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
