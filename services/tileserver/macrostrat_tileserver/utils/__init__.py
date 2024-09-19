from contextvars import ContextVar
from enum import Enum
from pathlib import Path

from .cache import CacheMode, CacheStatus
from .output import TileResponse, DecimalJSONResponse, VectorTileResponse


def scales_for_zoom(z: int, dz: int = 0):
    _z = z - dz
    if _z < 3:
        return "tiny", ["tiny"]
    elif _z < 6:
        return "small", ["tiny", "small"]
    elif _z < 9:
        return "medium", ["small", "medium"]
    else:
        return "large", ["medium", "large"]


class MapCompilation(str, Enum):
    Carto = "carto"
    Maps = "maps"


_query_index = ContextVar("query_index", default={})


def _update_query_index(key, value):
    _query_index.set({**_query_index.get(), key: value})


def get_sql(filename: Path):
    ix = _query_index.get()
    if filename in ix:
        return ix[filename]

    q = filename.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]
    _update_query_index(filename, q)
    return q


def get_layer_sql(base_dir: Path, filename: str, as_mvt: bool = True):
    if not filename.endswith(".sql"):
        filename += ".sql"

    q = get_sql(base_dir / filename)

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    if as_mvt:
        # Wrap with MVT creation
        return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"

    return q


def prepared_statement(id):
    """Legacy prepared statement"""
    filename = Path(__file__).parent.parent / "sql" / f"{id}.sql"
    return get_sql(filename)
