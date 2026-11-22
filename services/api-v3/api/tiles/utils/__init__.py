from enum import Enum
from pathlib import Path

from macrostrat.tileserver_utils import get_sql


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
