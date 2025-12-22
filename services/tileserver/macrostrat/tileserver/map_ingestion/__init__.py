from enum import Enum
from pathlib import Path

from asyncpg import UndefinedTableError
from buildpg import Renderer, render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes
from titiler.core.models.mapbox import TileJSON

from macrostrat.database.utils import format as format_sql
from macrostrat.utils import get_logger

print_sql_statements = False

router = APIRouter()
log = get_logger("uvicorn.error")

__here__ = Path(__file__).parent


class FeatureType(str, Enum):
    """Feature types."""

    polygons = "polygons"
    lines = "lines"
    points = "points"


@router.get(
    "/{slug}/tilejson.json",
    response_model=TileJSON,
    responses={200: {"description": "Return a tilejson"}},
    response_model_exclude_none=True,
)
async def tilejson(
    request: Request,
    slug: str,
):
    """Return TileJSON document."""
    url_path = request.url_for(
        "tile", **{"slug": slug, "z": "{z}", "x": "{x}", "y": "{y}"}
    )
    # TODO url_for resolves to http rather than https. find a better solution
    tile_endpoint = str(url_path)
    tile_endpoint = tile_endpoint.replace("http://", "https://")
    base_queries = [
        f"SELECT geom FROM sources.{slug}_polygons",
        f"SELECT geom FROM sources.{slug}_lines",
        f"SELECT geom FROM sources.{slug}_points",
    ]

    bounds = None
    pool = request.app.state.pool
    async with pool.acquire() as con:
        for i in range(len(base_queries), 0, -1):
            try:
                bounds_query = " UNION ".join(base_queries[:i])
                sql = get_bounds(bounds_query, geometry_column="geom")
                bounds = await con.fetchval(sql)
                break
            except UndefinedTableError:
                continue

    if bounds is None:
        return Response(status_code=404, content=f"No geometry tables found for {slug}")

    return {
        "minzoom": 0,
        "maxzoom": 18,
        "name": slug,
        "bounds": bounds,
        "tiles": [tile_endpoint],
    }


@router.get("/{slug}/{z}/{x}/{y}")
async def tile(
    request: Request,
    slug: str,
    z: int,
    x: int,
    y: int,
):

    # if feature_type != FeatureType.polygons:
    #    return Response(status_code=404, content="Only polygons are supported for now")

    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    data = b""
    success = False

    for layer in FeatureType:

        try:
            data += await get_layer(pool, slug, layer, z=z, x=x, y=y)
            success = True
        except UndefinedTableError:
            pass
    if not success:
        return Response(status_code=404, content=f"No tables found for {slug}")

    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


async def get_layer(pool, slug, layer: FeatureType, **params):
    async with pool.acquire() as con:

        table_name = f"{slug}_{layer.value}"
        alias = "s"
        column_dict = await get_table_columns(con, table_name, schema="sources")

        log.debug("Columns: %s", column_dict)
        columns = [
            format_column(k, v, cast_empty_strings=True, table_alias=alias)
            for k, v in column_dict.items()
            if k != "geom"
        ]
        columns.append("tile_layers.tile_geom(s.geom, :envelope) AS geometry")

        joins = None
        if layer == FeatureType.polygons:
            joins = [
                "LEFT JOIN macrostrat.intervals i0 ON s.b_interval = i0.id",
                "LEFT JOIN macrostrat.intervals i1 ON s.t_interval = i1.id",
            ]

            b_age = "i0.age_bottom"
            t_age = "i1.age_top"
            # Eventually we will allow b_age and t_age to be set directly
            # b_age = "coalesce(s.b_age, i0.age_bottom)"
            # t_age = "coalesce(s.t_age, i1.age_top)"
            columns += [
                b_age + "::float AS b_age",
                t_age + "::float AS t_age",
                _color_subquery(b_age, t_age, "color"),
            ]

        return await run_layer_query(
            con,
            f"sources.{table_name}",
            columns,
            joins=joins,
            table_alias=alias,
            layer_name=f"{layer.value}",
            **params,
        )


string_data_types = [
    "character varying",
    "text",
]


def format_column(
    col, data_type, table_alias=None, cast_empty_strings=False, name=None
):
    val = _wrap_with_quotes(col)
    if name is None:
        name = val
    if table_alias is not None:
        val = f"{table_alias}.{val}"
    if cast_empty_strings and data_type in string_data_types:
        val = f"NULLIF({val}, '')::text"
    return f"{val} AS {name}"


def _color_subquery(b_age, t_age, alias):
    return f"""(
    SELECT interval_color
      FROM macrostrat.intervals
      WHERE age_top <= {t_age} AND age_bottom >= {b_age}
      ORDER BY age_bottom - age_top
      LIMIT 1
    ) AS {alias}"""


async def run_layer_query(
    con,
    table_name,
    columns,
    *,
    joins=None,
    layer_name="default",
    table_alias=None,
    **params,
):
    _cols = ", ".join(columns)
    query = f"SELECT {_cols} FROM {table_name}"
    if table_alias:
        query += f" AS {table_alias}"

    if joins:
        query += "\n" + "\n".join(joins)

    query = extend_sql(query)
    params = dict(layer_name=layer_name, **params)
    print("\nRunning query:", query)
    print("\nParams:", params)

    if print_sql_statements:
        log.debug(
            "Running query:\n%s\nParameters: %s",
            format_sql(query, reindent=True),
            params,
        )

    q, p = render(query, **params)

    return await con.fetchval(q, *p)


def _wrap_with_quotes(col):
    if col[0] == '"' and col[-1] == '"':
        col = col[1:-1]
    if '"' in col:
        col = col.replace('"', '""')
    return '"' + col + '"'


def extend_sql(sql):
    q = sql.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name, 4096, 'geometry') FROM feature_query"


def get_bounds(base_query, geometry_column="geometry"):
    return f"""WITH b AS (
        SELECT ST_Union(a.{geometry_column}::box2d)::box2d env
        FROM ({base_query}) a
    )
    SELECT ARRAY[ST_XMin(env), ST_YMin(env), ST_XMax(env), ST_YMax(env)]
    FROM b;
    """


async def get_table_columns(con, table, schema="sources"):
    base_sql = f"""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = :table
    AND table_schema = :schema;
    """
    print("table", table, "schema", schema)

    q, p = render(base_sql, table=table, schema=schema)
    print("variables erroring", p, q)
    res = await con.fetch(q, *p)
    if len(res) == 0:
        raise UndefinedTableError(f"Table {schema}.{table} not found")

    return {i[0]: i[1] for i in res}


def register_map_ingestion_routes(app):
    app.include_router(router, tags=["Map ingestion"], prefix="/ingestion")
