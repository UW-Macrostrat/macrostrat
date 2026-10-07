"""
`PATCH /columns/{col_id}/geometry`: a column's footprint, written without
re-ingesting the column.

The footprint is a point (where the column was measured) and a region (the area it
stands for). Both go through `macrostrat.column_utils`, as the importer's do; a point
given with a region is kept, and must lie inside it. Lines and uncertainty radii have
nowhere to be stored yet, so they are accepted and reported back as warnings.
"""

from typing import Literal, Union

from fastapi import APIRouter, Depends, HTTPException
from geojson_pydantic import LineString, MultiPolygon, Point, Polygon
from pydantic import BaseModel

from api.database import DatabaseDep
from api.routes.security import has_access
from macrostrat.column_utils import (
    GeometryError,
    resolve_geometry,
    write_column_footprint,
)

router = APIRouter(prefix="/columns", tags=["columns"])


class ColumnGeometryUpdate(BaseModel):
    point: Point | None = None
    region: Union[Polygon, MultiPolygon] | None = None
    line: LineString | None = None
    radius_km: float | None = None


class Notice(BaseModel):
    level: Literal["info", "warning", "error"]
    code: str
    message: str


class ColumnGeometryResult(BaseModel):
    col_id: int
    lat: float
    lng: float
    col_area: float
    notices: list[Notice]


def unsupported_notices(update: ColumnGeometryUpdate) -> list[Notice]:
    notices = []
    if update.line is not None:
        notices.append(
            Notice(
                level="warning",
                code="line-not-stored",
                message="Column lines aren't stored yet; the line was not saved.",
            )
        )
    if update.radius_km is not None:
        notices.append(
            Notice(
                level="warning",
                code="radius-not-stored",
                message="Location uncertainty isn't stored yet; the radius was not saved.",
            )
        )
    return notices


@router.patch("/{col_id}/geometry")
def update_column_geometry(
    col_id: int,
    update: ColumnGeometryUpdate,
    database: DatabaseDep,
    user_has_access: bool = Depends(has_access),
) -> ColumnGeometryResult:
    if not user_has_access:
        raise HTTPException(
            status_code=401, detail="User does not have access to edit columns"
        )

    lat = lng = None
    if update.point is not None:
        lng, lat = update.point.coordinates[:2]
    region = None
    if update.region is not None:
        region = update.region.wkt

    with database.sync_connection() as conn:
        try:
            geometry = resolve_geometry(
                conn,
                lat=lat,
                lng=lng,
                geom=region,
                label=f"Column {col_id}",
                keep_point=True,
            )
        except GeometryError as err:
            raise HTTPException(status_code=422, detail=str(err))
        if not write_column_footprint(conn, col_id, geometry):
            raise HTTPException(status_code=404, detail=f"No column {col_id}")

    return ColumnGeometryResult(
        col_id=col_id,
        lat=geometry.lat,
        lng=geometry.lng,
        col_area=geometry.area_km2,
        notices=unsupported_notices(update),
    )
