from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/tile/{z}/{x}/{y}")
async def tile_query(
    request: Request,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    where = ""

    params = {
        "z": z,
        "x": x,
        "y": y,
    }

    if "measurement_id" in request.query_params:
        measurement_id_vals = request.query_params["measurement_id"].split(",")
        measurement_id_vals = [int(v.strip()) for v in measurement_id_vals if v.strip()]
        where += " AND measurement_id = ANY(:measurement_id_vals)"
        params["measurement_id_vals"] = measurement_id_vals

    if "cluster" in request.query_params:
        cluster_val = request.query_params["cluster"]
        cluster = cluster_val.lower() not in ("false", "0", "no")

    else:
        cluster = True

    clusterSQL = """
        ,

        mvt_features AS (
            SELECT id,
                    ST_SnapToGrid(geom, 256, 256) AS cluster_geom,
                    geom
            FROM points
        ),
        grouped_features AS (
            SELECT
                tile_utils.cluster_expansion_zoom(ST_Collect(geom), :z) AS expansion_zoom,
                count(*) AS n,
                st_centroid(ST_Collect(geom)) AS geom,
                CASE
                WHEN count(*) < 2 THEN string_agg(f.id::text, ',')
                ELSE null
                END AS id
            FROM mvt_features f
            GROUP BY cluster_geom
        )
        SELECT ST_AsMVT(row) AS mvt
        FROM (SELECT * FROM grouped_features) AS row;
    """

    unclusteredSQL = """
        SELECT ST_AsMVT(
                points.*,
                'default',
                4096,
                'geom'
            ) AS mvt
            FROM points
    """

    if cluster:
        ending = clusterSQL
    else:
        ending = unclusteredSQL

    query = f"""
        WITH
            tile AS (
                SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
                    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326
            ),
            points AS (
                SELECT
                    id,
                    measurement_id,
                    tile_layers.tile_geom(
                        ST_Intersection(geometry, envelope_4326),
                        envelope
                    ) AS geom
                FROM macrostrat_api.measurements_with_type
                JOIN tile ON true
                WHERE
                    lat IS NOT NULL AND lng IS NOT NULL
                    AND ST_Intersects(
                        ST_SetSRID(ST_MakePoint(lng, lat), 4326),
                        envelope_4326
                    )
                    {where}
            )
            {ending}
    """

    q, p = render(query, **params)
    q = q.replace("textarray", "text[]")

    async with pool.acquire() as con:
        data = await con.fetchval(q, *p)

    return Response(data, media_type=MimeTypes.pbf.value)
