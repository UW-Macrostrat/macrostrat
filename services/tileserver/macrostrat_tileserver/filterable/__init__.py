from asyncio import gather
from typing import List
from enum import Enum
from pathlib import Path

from buildpg import V, render, Empty, funcs
from fastapi import APIRouter, Request, Response, Query
from timvt.resources.enums import MimeTypes


class Compilation(str, Enum):
    Carto = "carto"
    Maps = "maps"


router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/{compilation}/{z}/{x}/{y}")
async def get_tile(
        request: Request,
        compilation: Compilation,
        z: int,
        x: int,
        y: int,
        lithology: List[str] = Query(None)
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    if z < 3:
        # Select from carto.tiny table
        mapsize = "tiny"
        linesize = ["tiny"]
    elif z < 6:
        mapsize = "small"
        linesize = ["tiny", "small"]
    elif z < 9:
        mapsize = "medium"
        linesize = ["small", "medium"]
    else:
        mapsize = "large"
        linesize = ["medium", "large"]

    compilation_name = compilation.value
    where_lithology = get_lithology_clause(lithology)

    async with pool.acquire() as con:
        units_ = await run_layer_query(
            con,
            "units",
            z=z,
            x=x,
            y=y,
            mapsize=mapsize,
            compilation=V(compilation_name + ".polygons"),
            where_lithology=where_lithology
        )
        lines_ = await run_layer_query(
            con,
            "lines",
            z=z,
            x=x,
            y=y,
            mapsize=mapsize,
            linesize=linesize,
            compilation=V(compilation_name + ".lines")
        )
    data = join_layers([units_, lines_])
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


def get_lithology_clause(lithologies: List[str]):

    LITHOLOGY_COLUMNS = [
        "liths.lith_group",
        "liths.lith_class",
        "liths.lith_type",
        "liths.lith",
    ]

    if lithologies is None or len(lithologies) == 0:
        return Empty()

    return Empty() & funcs.OR(*map(lambda l: V(l) == funcs.any(funcs.cast(lithologies, "textarray")), LITHOLOGY_COLUMNS))


def join_layers(layers):
    """Join tiles together."""
    return b"".join(layers)


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(layer_name)
    q, p = render(query, layer_name=layer_name, **params)

    # Overcomes a shortcoming in buildpg that deems casting to an array as unsafe
    # https://github.com/samuelcolvin/buildpg/blob/e2a16abea5c7607b53c501dbae74a5765ba66e15/buildpg/components.py#L21
    q = q.replace("textarray", "text[]")

    print(q,p)

    return await con.fetchval(q, *p)


def get_layer_sql(layer: str):
    query = __here__ / "queries" / (layer + ".sql")

    q = query.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"
