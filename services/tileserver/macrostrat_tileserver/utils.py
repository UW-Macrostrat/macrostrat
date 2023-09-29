from pathlib import Path
from starlette.responses import Response
from timvt.resources.enums import MimeTypes
from enum import Enum
import titiler

class CacheMode(str, Enum):
    prefer = "prefer"
    force = "force"
    bypass = "bypass"


class CacheStatus(str, Enum):
    hit = "hit"
    miss = "miss"
    bypass = "bypass"


stmt_cache = {}


def prepared_statement(id):
    cached = stmt_cache.get(id)
    if cached is None:
        stmt_cache[id] = (Path(__file__).parent / "sql" / f"{id}.sql").open("r").read()
    return stmt_cache[id]


def TileResponse(content, timer, cache_status: CacheStatus = None, **kwargs):
    kwargs["headers"] = {
        "Server-Timing": timer.server_timings(),
        **kwargs.pop("headers", {}),
    }
    if cache_status is not None:
        kwargs["headers"]["X-Tile-Cache"] = cache_status
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(content, **kwargs)
