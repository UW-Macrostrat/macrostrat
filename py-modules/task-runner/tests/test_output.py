from macrostrat.task_runner.output import OutputStream, read_all


class FakeRedis:
    def __init__(self):
        self.entries = []

    def xadd(self, key, fields, maxlen=None, approximate=False):
        self.entries.append(
            (f"{len(self.entries) + 1}-0", {b"d": fields["d"].encode()})
        )

    def xrange(self, key, start, end):
        return list(self.entries)


def test_chunks_are_flushed_on_newline_and_on_flush():
    redis = FakeRedis()
    out = OutputStream(redis, "r1")
    out.write("\x1b[32mhello\x1b[0m")
    assert redis.entries == []
    out.write(" world\n")
    assert len(redis.entries) == 1
    out.write("\x1b[1A\rprogress 50%")
    out.flush()
    assert read_all(redis, "r1") == "\x1b[32mhello\x1b[0m world\n\x1b[1A\rprogress 50%"


def test_stream_reads_as_a_terminal():
    out = OutputStream(FakeRedis(), "r1")
    assert out.isatty() and out.writable() and out.encoding == "utf-8"
