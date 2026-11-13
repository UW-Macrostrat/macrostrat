"""References, with enough about their geometries to diagnose a bad one.

`rgeom` places a reference on the ground, and matching uses it to place names
that have no footprint of their own. A reference whose geometry is wrong places
them wrongly. `/refs` describes the geometries; `/refs.geojson` is the same rows
with the geometries themselves, unsimplified, so a defect shows as stored.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from api.database import DatabaseDep

router = APIRouter(prefix="/refs", tags=["refs"])

HasGeom = Annotated[
    Optional[bool], Query(description="Only references with (or without) one")
]
RefIds = Annotated[Optional[list[int]], Query(description="Only these references")]


class Reference(BaseModel):
    id: int
    pub_year: int
    author: str
    ref: str
    doi: Optional[str] = None
    url: Optional[str] = None
    compilation_code: str
    #: Strat names contributed by this reference.
    n_strat_names: int
    geom_type: Optional[str] = None
    n_points: Optional[int] = None
    srid: Optional[int] = None
    #: `[minx, miny, maxx, maxy]`.
    bbox: Optional[list[float]] = None
    is_valid: Optional[bool] = None
    invalid_reason: Optional[str] = None


@router.get("", summary="References and the shape of their geometries")
def list_refs(
    database: DatabaseDep, has_geom: HasGeom = None, ref_id: RefIds = None
) -> list[Reference]:
    clauses, params = _filters(has_geom, ref_id)
    rows = database.sync.run_query(_select(clauses), params).all()
    return [Reference(**row._mapping) for row in rows]


@router.get(
    ".geojson",
    summary="References as a GeoJSON FeatureCollection",
    response_class=Response,
    responses={200: {"content": {"application/geo+json": {}}}},
)
def list_refs_geojson(
    database: DatabaseDep, has_geom: HasGeom = None, ref_id: RefIds = None
) -> Response:
    clauses, params = _filters(has_geom, ref_id)
    # Serialized in Postgres: a geometry can run to tens of thousands of vertices.
    collection = database.sync.run_query(
        f"""
        SELECT json_build_object(
          'type', 'FeatureCollection',
          'features', coalesce(json_agg(json_build_object(
            'type', 'Feature',
            'id', r.id,
            'geometry', ST_AsGeoJSON(r.geom, 5)::json,
            'properties', to_jsonb(r) - 'geom'
          ) ORDER BY r.id), '[]'::json)
        )::text
        FROM ({_select(clauses, geometry=True)}) r
        """,
        params,
    ).scalar()
    return Response(collection, media_type="application/geo+json")


@router.get("/{ref_id}", summary="A reference and the shape of its geometry")
def get_ref(ref_id: int, database: DatabaseDep) -> Reference:
    row = database.sync.run_query(
        _select(["r.id = :ref_id"]), dict(ref_id=ref_id)
    ).first()
    if row is None:
        raise HTTPException(404, f"No reference {ref_id}")
    return Reference(**row._mapping)


def _filters(has_geom: Optional[bool], ref_ids: Optional[list[int]]):
    clauses = []
    params = {}
    if has_geom is not None:
        clauses.append(f"r.rgeom IS {'NOT ' if has_geom else ''}NULL")
    if ref_ids:
        clauses.append("r.id = ANY(:ref_ids)")
        params["ref_ids"] = ref_ids
    return clauses, params


def _select(clauses: list[str], *, geometry: bool = False) -> str:
    geom = ""
    if geometry:
        geom = ", r.rgeom AS geom"
    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)

    return f"""
        WITH names AS (
          SELECT ref_id, count(*) AS n
          FROM macrostrat.strat_names
          GROUP BY ref_id
        )
        SELECT r.id, r.pub_year, r.author, r.ref, r.doi, r.url,
          r.compilation_code::text AS compilation_code,
          coalesce(names.n, 0) AS n_strat_names,
          GeometryType(r.rgeom) AS geom_type,
          ST_NPoints(r.rgeom) AS n_points,
          ST_SRID(r.rgeom) AS srid,
          CASE WHEN r.rgeom IS NOT NULL THEN ARRAY[
            ST_XMin(r.rgeom), ST_YMin(r.rgeom), ST_XMax(r.rgeom), ST_YMax(r.rgeom)
          ] END AS bbox,
          ST_IsValid(r.rgeom) AS is_valid,
          CASE WHEN NOT ST_IsValid(r.rgeom)
            THEN ST_IsValidReason(r.rgeom) END AS invalid_reason
          {geom}
        FROM macrostrat.refs r
        LEFT JOIN names ON names.ref_id = r.id
        {where}
        ORDER BY r.id
    """
