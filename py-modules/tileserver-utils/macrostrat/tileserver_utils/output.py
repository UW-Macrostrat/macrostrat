import decimal
import json
import typing
from enum import Enum
from typing import Iterable, Optional

from starlette.responses import JSONResponse, Response

#: Names the maps a tile draws, as ascending `source_id`s, comma-separated.
SOURCES_HEADER = "X-Macrostrat-Sources"


def sources_header(source_ids: Optional[Iterable[int]]) -> Optional[str]:
    """The `X-Macrostrat-Sources` value for a tile, or None when it names none."""
    if not source_ids:
        return None
    return ",".join(str(i) for i in sorted(set(source_ids)))


class MimeTypes(str, Enum):
    """Responses MineTypes."""

    xml = "application/xml"
    json = "application/json"
    geojson = "application/geo+json"
    html = "text/html"
    text = "text/plain"
    pbf = "application/x-protobuf"
    mvt = "application/x-protobuf"


def TileResponse(
    content,
    timer,
    cache_status: "CacheStatus" = None,
    sources: Optional[Iterable[int]] = None,
    **kwargs,
):
    kwargs["headers"] = {
        "Server-Timing": timer.server_timings(),
        **kwargs.pop("headers", {}),
    }
    if cache_status is not None:
        kwargs["headers"]["X-Tile-Cache"] = cache_status
    header = sources_header(sources)
    if header is not None:
        kwargs["headers"][SOURCES_HEADER] = header
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


class VectorTileResponse(Response):
    media_type = MimeTypes.pbf.value

    def __init__(self, *layers, **kwargs):
        data = join_layers(layers)
        kwargs.setdefault("media_type", MimeTypes.pbf.value)
        super().__init__(data, **kwargs)


def join_layers(layers):
    """Join tiles together."""
    return b"".join(layers)
