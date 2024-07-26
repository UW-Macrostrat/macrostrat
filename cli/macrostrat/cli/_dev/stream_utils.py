import asyncio
import zlib

from aiofiles.threadpool import AsyncBufferedIOBase
from macrostrat.utils import get_logger
from .utils import console

log = get_logger(__name__)


async def print_stream_progress(
    in_stream: asyncio.StreamReader,
    out_stream: asyncio.StreamWriter | AsyncBufferedIOBase | None,
):
    """This should be unified with print_stream_progress, but there seem to be
    slight API differences between aiofiles and asyncio.StreamWriter APIs.?"""
    megabytes_written = 0
    i = 0
    async for line in in_stream:
        megabytes_written += len(line) / 1_000_000
        if isinstance(out_stream, AsyncBufferedIOBase):
            await out_stream.write(line)
            await out_stream.flush()
        elif out_stream is not None:
            out_stream.write(line)
            await out_stream.drain()
        i += 1
        if i == 1000:
            i = 0
            _print_progress(megabytes_written, end="\r")

    if out_stream is not None:
        out_stream.close()
    _print_progress(megabytes_written)


def _print_progress(megabytes: float, **kwargs):
    progress = f"Dumped {megabytes:.1f} MB"
    print(progress, **kwargs)


async def print_stdout(stream: asyncio.StreamReader):
    async for line in stream:
        console.print(line.decode("utf-8"), style="dim")


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
