import decimal
import json
import typing

from starlette.responses import JSONResponse, Response
from timvt.resources.enums import MimeTypes
from .cache import CacheStatus

def TileResponse(content, timer, cache_status: CacheStatus = None, **kwargs):
    kwargs["headers"] = {
        "Server-Timing": timer.server_timings(),
        **kwargs.pop("headers", {}),
    }
    if cache_status is not None:
        kwargs["headers"]["X-Tile-Cache"] = cache_status
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(content, **kwargs)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


class DecimalJSONResponse(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=DecimalEncoder,
        ).encode("utf-8")
