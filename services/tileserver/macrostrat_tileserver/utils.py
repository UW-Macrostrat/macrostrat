from pathlib import Path
from starlette.responses import Response
from timvt.resources.enums import MimeTypes

stmt_cache = {}


def prepared_statement(id):
    cached = stmt_cache.get(id)
    if cached is None:
        stmt_cache[id] = (Path(__file__).parent / "sql" / f"{id}.sql").open("r").read()
    return stmt_cache[id]


def TileResponse(content, timer, cache_hit=False, **kwargs):
    kwargs["headers"] = {
        "Server-Timing": timer.server_timings(),
        "X-Tile-Cache": "hit" if cache_hit else "miss",
        **kwargs.pop("headers", {}),
    }
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(content, **kwargs)
