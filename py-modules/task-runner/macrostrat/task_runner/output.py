"""The run's output stream: a Redis stream of raw terminal chunks."""

import io

# Enough for hours of progress-bar redraws; the ledger keeps the archive.
MAXLEN = 100_000
# The stream outlives the run long enough to be replayed, then the row's copy serves.
STREAM_TTL_SECONDS = 7 * 24 * 3600


def output_key(run_id: str) -> str:
    return f"task-run:{run_id}:out"


def control_channel(run_id: str) -> str:
    return f"task-run:{run_id}:ctl"


class OutputStream(io.TextIOBase):
    """A text sink that appends each flushed chunk to the run's stream.

    Chunks keep their ANSI sequences, so a terminal in the browser renders what
    a terminal on the worker would have. Rich flushes after every print and
    every live-display frame; a plain `print` is flushed on its newline.
    """

    def __init__(self, redis, run_id: str, *, maxlen: int = MAXLEN):
        self.redis = redis
        self.key = output_key(run_id)
        self.maxlen = maxlen
        self._buffer: list[str] = []

    @property
    def encoding(self):
        return "utf-8"

    def writable(self):
        return True

    def isatty(self):
        return True

    def write(self, text: str) -> int:
        self._buffer.append(text)
        if "\n" in text:
            self.flush()
        return len(text)

    def flush(self):
        if not self._buffer:
            return
        data = "".join(self._buffer)
        self._buffer.clear()
        self.redis.xadd(self.key, {"d": data}, maxlen=self.maxlen, approximate=True)


def read_all(redis, run_id: str) -> str:
    """The whole stream as one string, for archiving."""
    entries = redis.xrange(output_key(run_id), "-", "+")
    return "".join(_text(fields[b"d"]) for _, fields in entries)


def expire(redis, run_id: str, ttl: int = STREAM_TTL_SECONDS) -> None:
    redis.expire(output_key(run_id), ttl)


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
