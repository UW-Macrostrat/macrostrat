"""The cache helper's contract for a tile's sources: a renderer may hand
back bytes or a `RenderedTile`, the header follows, and a hit answers with the
sources stored beside the tile. Database-free, with a stand-in pool."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks
from morecantile import Tile
from starlette.requests import Request

from macrostrat.tileserver_utils import (
    SOURCES_HEADER,
    CachedTileArgs,
    CacheMode,
    RenderedTile,
    handle_cached_tile_request,
    sources_header,
)


class TestSourcesHeader:
    def test_ids_ascending_and_deduplicated(self):
        assert sources_header([3401, 133, 3401, 7]) == "7,133,3401"

    def test_nothing_drawn_means_no_header(self):
        assert sources_header([]) is None
        assert sources_header(None) is None


class FakeConn:
    def __init__(self, row):
        self.row = row
        self.executed = []

    async def fetchrow(self, q, *p):
        return self.row

    async def execute(self, q, *p):
        self.executed.append(p)


class FakePool:
    """Answers every cache lookup with one row (or none)."""

    def __init__(self, row=None):
        self.conn = FakeConn(row)

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def request():
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def args(mode):
    # An integer layer is a resolved profile id: no lookup needed.
    return CachedTileArgs(
        layer=1, tile=Tile(1, 2, 3), media_type="application/x-protobuf", mode=mode
    )


def run(get_tile, mode, pool=None):
    """Serve one request and run its background tasks (the cache write)."""

    async def go():
        tasks = BackgroundTasks()
        res = await handle_cached_tile_request(
            request(), pool or FakePool(), tasks, get_tile, args(mode)
        )
        await tasks()
        return res

    return asyncio.run(go())


def test_a_renderer_naming_sources_sets_the_header():
    async def get_tile(req, a):
        return RenderedTile(b"tile", [3401, 133])

    res = run(get_tile, CacheMode.bypass)
    assert res.body == b"tile"
    assert res.headers[SOURCES_HEADER] == "133,3401"


def test_plain_bytes_still_work_and_name_nothing():
    async def get_tile(req, a):
        return b"tile"

    res = run(get_tile, CacheMode.bypass)
    assert res.body == b"tile"
    assert SOURCES_HEADER not in res.headers


def test_a_hit_answers_with_the_stored_sources():
    async def get_tile(req, a):
        raise AssertionError("a hit must not render")

    pool = FakePool({"tile": b"cached", "sources": [7, 9]})
    res = run(get_tile, CacheMode.prefer, pool)
    assert res.body == b"cached"
    assert res.headers["X-Tile-Cache"] == "hit"
    assert res.headers[SOURCES_HEADER] == "7,9"


def test_a_miss_stores_the_sources_with_the_tile():
    async def get_tile(req, a):
        return RenderedTile(b"tile", [5])

    pool = FakePool(None)
    res = run(get_tile, CacheMode.prefer, pool)
    assert res.headers["X-Tile-Cache"] == "miss"
    (params,) = pool.conn.executed
    assert b"tile" in params and [5] in params
