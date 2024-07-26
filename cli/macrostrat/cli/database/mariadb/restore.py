import asyncio
from pathlib import Path
from typing import Optional
from sys import stdin

from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine
from macrostrat.core.exc import MacrostratError
import aiofiles

from .utils import build_connection_args
from macrostrat.core.config import docker_internal_url

from ..._dev.utils import (
    _create_command,
    _create_database_if_not_exists,
    print_stdout,
    print_stream_progress,
)

console = Console()

log = get_logger(__name__)


def restore_mariadb(_input: Optional[str], engine: Engine, *args, **kwargs):
    """Restore a MariaDB database from a dump file or stream"""

    if _input.startswith("http"):
        raise NotImplementedError("HTTP(S) restore not yet implemented")

    if _input is not None:
        _input = Path(_input)

    if _input is None:
        if stdin.isatty():
            raise MacrostratError("No input file specified")

        # Read from stdin
        _input = Path("/dev/stdin")

    if not _input.is_file():
        raise MacrostratError(f"{_input} is not a file")

    task = _restore_mariadb_from_file(_input, engine, *args, **kwargs)
    asyncio.run(task)


async def _restore_mariadb(engine: Engine, *args, **kwargs):
    """Load MariaDB dump (GZipped SQL file) into a database."""
    overwrite = kwargs.pop("overwrite", False)
    create = kwargs.pop("create", overwrite)
    container = kwargs.pop("container", "mariadb:10.10")

    _create_database_if_not_exists(
        engine.url, create=create, allow_exists=False, overwrite=overwrite
    )
    conn = build_connection_args(docker_internal_url(engine.url))

    # Run pg_restore in a local Docker container
    # TODO: this could also be run with pg_restore in a Kubernetes pod
    # or another location, if more appropriate. Running on the remote
    # host, if possible, is probably the fastest option. There should be
    # multiple options ideally.
    _cmd = _create_command(
        "mariadb",
        *conn,
        *args,
        container=container,
    )

    log.debug(" ".join(_cmd))

    return await asyncio.create_subprocess_exec(
        *_cmd,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 1024 * 1,  # 1 MB windows
    )


async def _restore_mariadb_from_file(dumpfile: Path, engine: Engine, *args, **kwargs):
    proc = await _restore_mariadb(engine, *args, **kwargs)
    # Open dump file as an async stream
    async with aiofiles.open(dumpfile, mode="rb") as source:
        s1 = DecodingStreamReader(source)
        await asyncio.gather(
            asyncio.create_task(
                print_stream_progress(s1, proc.stdin),
            ),
            asyncio.create_task(print_stdout(proc.stderr)),
        )

        # asyncio.create_task(print_stdout(proc.stderr)),


import zlib


class DecodingStreamReader(asyncio.StreamReader):
    """A StreamReader that decompresses gzip files and decodes bytes to strings"""

    # https://ejosh.co/de/2022/08/stream-a-massive-gzipped-json-file-in-python/

    def __init__(self, stream, encoding="utf-8", errors="strict"):
        super().__init__()
        self.stream = stream
        self._is_gzipped = None
        self.d = zlib.decompressobj(zlib.MAX_WBITS | 16)

    def decompress(self, input: bytes) -> bytes:
        decompressed = self.d.decompress(input)
        data = b""
        while self.d.unused_data != b"":
            buf = self.d.unused_data
            self.d = zlib.decompressobj(zlib.MAX_WBITS | 16)
            data = self.d.decompress(buf)
        return decompressed + data

    def transform_data(self, data):
        if self._is_gzipped is None:
            self._is_gzipped = data[:2] == b"\x1f\x8b"
            log.info("is_gzipped: %s", self._is_gzipped)
        if self._is_gzipped:
            # Decompress the data
            data = self.decompress(data)
        return data

    async def read(self, n=-1):
        data = await self.stream.read(n)
        return self.transform_data(data)

    async def readline(self):
        res = b""
        while res == b"":
            # Read next line
            line = await self.stream.readline()
            if not line:
                break
            res += self.transform_data(line)
        return res
