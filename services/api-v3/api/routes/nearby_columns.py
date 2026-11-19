"""
`GET /columns/{col_id}/nearby`: columns of other projects covering the same ground.

Projects compiled independently over one region (GBDB and ChinaLex, say) are not
drawn together on any map, so this is how a column page links across to them.

A column's footprint is its region where it has one, else its point. Two columns
*overlap* when their footprints share interior — a point inside a region, or two
regions overlapping — so Voronoi neighbours that only share an edge do not. Other
columns within `radius_km` come back as *nearby*, which is the only way two
point-only columns can meet.
"""

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from api.database import DatabaseDep

router = APIRouter(prefix="/columns", tags=["columns"])

NEARBY_COLUMNS = text("""
WITH subject AS (
  SELECT
    c.id,
    c.project_id,
    coalesce(c.poly_geom, c.coordinate) AS footprint,
    coalesce(c.coordinate, ST_PointOnSurface(c.poly_geom)) AS point,
    -- Planar `&&` against a geodesic reach, so the indexes still apply;
    -- a zero buffer would empty a point
    CASE WHEN CAST(:radius_km AS float) > 0 THEN ST_Buffer(
      coalesce(c.poly_geom, c.coordinate)::geography,
      CAST(:radius_km AS float) * 1000
    )::geometry ELSE coalesce(c.poly_geom, c.coordinate) END AS reach
  FROM macrostrat.cols c
  WHERE c.id = :col_id
),
-- Regions and point-only columns, each through its own spatial index
candidates AS (
  SELECT c.id, c.poly_geom AS footprint, c.coordinate AS point
  FROM macrostrat.cols c, subject s
  WHERE c.poly_geom && s.reach
    AND ST_Intersects(c.poly_geom, s.reach)
  UNION ALL
  SELECT c.id, c.coordinate, c.coordinate
  FROM macrostrat.cols c, subject s
  WHERE c.poly_geom IS NULL
    AND c.coordinate && s.reach
    AND ST_Intersects(c.coordinate, s.reach)
),
matched AS (
  SELECT
    c.id,
    c.col_name,
    c.col_group_id,
    c.project_id,
    c.status_code::text AS status_code,
    ST_Relate(k.footprint, s.footprint, 'T********') AS overlaps,
    ST_Distance(
      coalesce(k.point, ST_PointOnSurface(k.footprint))::geography,
      s.point::geography
    ) / 1000 AS distance_km,
    -- Share of this column's region the other one covers; regions only
    CASE
      WHEN ST_Dimension(k.footprint) = 2 AND ST_Dimension(s.footprint) = 2
      THEN least(
        ST_Area(ST_Intersection(k.footprint, s.footprint)::geography)
          / nullif(ST_Area(s.footprint::geography), 0),
        1
      )
    END AS overlap_fraction
  FROM candidates k
  JOIN macrostrat.cols c ON c.id = k.id
  CROSS JOIN subject s
  WHERE c.id <> s.id
    AND c.status_code <> 'obsolete'
    AND (CAST(:include_same_project AS boolean) OR c.project_id <> s.project_id)
),
ranked AS (
  SELECT
    m.*,
    row_number() OVER (
      PARTITION BY m.project_id ORDER BY m.overlaps DESC, m.distance_km
    ) AS rank,
    count(*) OVER (PARTITION BY m.project_id) AS n_project,
    count(*) FILTER (WHERE m.overlaps) OVER (PARTITION BY m.project_id)
      AS n_project_overlapping
  FROM matched m
)
SELECT
  r.id AS col_id,
  r.col_name,
  r.col_group_id,
  g.col_group,
  r.project_id,
  p.project,
  p.slug AS project_slug,
  r.status_code,
  CASE WHEN r.overlaps THEN 'overlaps' ELSE 'nearby' END AS relation,
  r.distance_km::float AS distance_km,
  r.overlap_fraction::float AS overlap_fraction,
  r.n_project,
  r.n_project_overlapping
FROM ranked r
JOIN macrostrat.projects p ON p.id = r.project_id
LEFT JOIN macrostrat.col_groups g ON g.id = r.col_group_id
WHERE r.rank <= :per_project
ORDER BY r.n_project_overlapping DESC, r.project_id, r.rank
""")


class NearbyColumn(BaseModel):
    col_id: int
    col_name: str
    col_group_id: Optional[int] = None
    col_group: Optional[str] = None
    status_code: str
    #: `overlaps` when the footprints share interior; `nearby` within the radius.
    relation: Literal["overlaps", "nearby"]
    #: Between the two columns' points.
    distance_km: float
    #: Share of the subject's region this column covers, when both are regions.
    overlap_fraction: Optional[float] = None


class NearbyProject(BaseModel):
    project_id: int
    project: str
    slug: Optional[str] = None
    #: Every match in the project, of which `columns` holds the nearest.
    n_columns: int
    n_overlapping: int
    columns: list[NearbyColumn]


class NearbyColumnsResult(BaseModel):
    col_id: int
    radius_km: float
    projects: list[NearbyProject]


@router.get("/{col_id}/nearby", summary="Columns of other projects at this place")
async def get_nearby_columns(
    col_id: int,
    database: DatabaseDep,
    radius_km: Annotated[
        float,
        Query(ge=0, le=500, description="Reach beyond the footprint for 'nearby'"),
    ] = 25,
    per_project: Annotated[
        int, Query(ge=1, le=500, description="Nearest columns to return per project")
    ] = 25,
    include_same_project: Annotated[
        bool, Query(description="Also return this column's own project")
    ] = False,
) -> NearbyColumnsResult:
    """Columns overlapping or near this one, grouped by project.

    Projects with the most overlapping columns come first; within a project,
    overlapping columns precede nearby ones, nearest first.
    """
    async with database.async_connection() as conn:
        exists = await conn.execute(
            text("SELECT 1 FROM macrostrat.cols WHERE id = :col_id"),
            {"col_id": col_id},
        )
        if exists.first() is None:
            raise HTTPException(404, f"No column {col_id}")
        res = await conn.execute(
            NEARBY_COLUMNS,
            {
                "col_id": col_id,
                "radius_km": radius_km,
                "per_project": per_project,
                "include_same_project": include_same_project,
            },
        )
        rows = res.mappings().all()

    projects: dict[int, NearbyProject] = {}
    for row in rows:
        project = projects.get(row["project_id"])
        if project is None:
            project = NearbyProject(
                project_id=row["project_id"],
                project=row["project"],
                slug=row["project_slug"],
                n_columns=row["n_project"],
                n_overlapping=row["n_project_overlapping"],
                columns=[],
            )
            projects[row["project_id"]] = project
        project.columns.append(NearbyColumn(**row))

    return NearbyColumnsResult(
        col_id=col_id, radius_km=radius_km, projects=list(projects.values())
    )
