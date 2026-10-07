"""Resolve a column's geometry, deriving what the database needs from what it is given.

`macrostrat.cols` carries five geometry-related columns, three of which are NOT NULL:
`lat`, `lng` and `col_area` (a geodesic area in km²), plus a nullable `coordinate` point,
`poly_geom` polygon and `wkt` text. A workbook supplies either a lat/lng pair or a polygon
in WKT, so the rest has to be derived.

All of that derivation happens **in PostGIS via `geoalchemy2`** rather than by hand:
geometry values are `WKTElement`s, which render as `ST_GeomFromEWKT(...)` and so carry
their SRID properly, and the derived scalars come from `geoalchemy2.functions`. Beyond
correctness this leaves room to grow — reprojection, topology checks, simplification are
all the same mechanism.
"""

from dataclasses import dataclass

from geoalchemy2 import Geography, WKTElement
from geoalchemy2 import functions as gfunc
from sqlalchemy import Connection, cast, select, text
from sqlalchemy.orm import Session

from macrostrat.utils import get_logger

log = get_logger(__name__)

SRID = 4326

#: A column given only a point has no footprint, and `cols.col_area` is NOT NULL.
POINT_AREA_KM2 = 0.0

_POLYGON_TYPES = {"POLYGON", "MULTIPOLYGON"}


class GeometryError(ValueError):
    """A column's geometry is missing, invalid, or of the wrong kind."""


@dataclass
class ColumnGeometry:
    """Everything `macrostrat.cols` needs to describe where a column is."""

    lat: float
    lng: float
    area_km2: float
    coordinate: WKTElement
    poly_geom: WKTElement | None = None
    wkt: str | None = None

    def column_values(self) -> dict:
        """The geometry-derived fields, ready to hand to a reconciler."""
        return {
            "lat": self.lat,
            "lng": self.lng,
            "col_area": self.area_km2,
            "coordinate": self.coordinate,
            "poly_geom": self.poly_geom,
            "wkt": self.wkt,
        }


def _point(lng: float, lat: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=SRID)


def resolve_geometry(
    conn: Connection | Session,
    *,
    lat: float | None = None,
    lng: float | None = None,
    geom: str | None = None,
    label: str = "column",
    keep_point: bool = False,
) -> ColumnGeometry:
    """Build a `ColumnGeometry` from a lat/lng pair, a polygon WKT, or both.

    When a polygon is given it is authoritative: `lat`/`lng` are derived from it with
    `ST_PointOnSurface` (which, unlike a centroid, is guaranteed to fall inside the
    polygon) and `col_area` from a geodesic `ST_Area` on the geography type. Any lat/lng
    the workbook also supplied is checked against the polygon rather than trusted.

    With `keep_point`, a supplied point is a deliberate location rather than a stand-in:
    it is kept when the polygon contains it, and is an error when it doesn't.
    """
    if geom is not None and str(geom).strip():
        return _from_polygon(
            conn,
            str(geom).strip(),
            lat=lat,
            lng=lng,
            label=label,
            keep_point=keep_point,
        )

    if lat is None or lng is None:
        raise GeometryError(
            f"{label}: needs either a lat/lng pair or a polygon `geom`; got neither."
        )
    lat, lng = float(lat), float(lng)
    return ColumnGeometry(
        lat=lat,
        lng=lng,
        area_km2=POINT_AREA_KM2,
        coordinate=_point(lng, lat),
        poly_geom=None,
        wkt=None,
    )


def _from_polygon(
    conn: Connection | Session,
    wkt: str,
    *,
    lat: float | None,
    lng: float | None,
    label: str,
    keep_point: bool,
) -> ColumnGeometry:
    element = WKTElement(wkt, srid=SRID)

    # One round trip validates the geometry and derives every scalar the row needs, so
    # the values that follow are plain numbers and bind like anything else.
    derived = (
        conn.execute(
            select(
                gfunc.ST_IsValid(element).label("valid"),
                gfunc.ST_IsValidReason(element).label("reason"),
                gfunc.GeometryType(element).label("geometry_type"),
                gfunc.ST_Y(gfunc.ST_PointOnSurface(element)).label("lat"),
                gfunc.ST_X(gfunc.ST_PointOnSurface(element)).label("lng"),
                # `WKTElement` proxies only `st_*` attributes, so use the standalone cast().
                (gfunc.ST_Area(cast(element, Geography)) / 1e6).label("area_km2"),
                (
                    gfunc.ST_Contains(element, _point(lng, lat)).label("contains_point")
                    if lat is not None and lng is not None
                    else gfunc.ST_IsValid(element).label("contains_point")
                ),
            )
        )
        .mappings()
        .one()
    )

    if not derived["valid"]:
        raise GeometryError(f"{label}: invalid geometry — {derived['reason']}")
    if derived["geometry_type"] not in _POLYGON_TYPES:
        raise GeometryError(
            f"{label}: geometry must be a POLYGON or MULTIPOLYGON, "
            f"got {derived['geometry_type']}"
        )
    has_point = lat is not None and lng is not None
    if keep_point and has_point:
        if not derived["contains_point"]:
            raise GeometryError(
                f"{label}: the point ({lat}, {lng}) is outside the polygon"
            )
        return ColumnGeometry(
            lat=float(lat),
            lng=float(lng),
            area_km2=derived["area_km2"],
            coordinate=_point(lng, lat),
            poly_geom=element,
            wkt=wkt,
        )
    if has_point and not derived["contains_point"]:
        # Not fatal: the polygon wins, but a disagreement usually means one of the two
        # is wrong and the operator should know which value was kept.
        log.warning(
            "%s: supplied lat/lng (%s, %s) falls outside its polygon; "
            "using the polygon's point-on-surface (%s, %s) instead",
            label,
            lat,
            lng,
            derived["lat"],
            derived["lng"],
        )

    return ColumnGeometry(
        lat=derived["lat"],
        lng=derived["lng"],
        area_km2=derived["area_km2"],
        coordinate=_point(derived["lng"], derived["lat"]),
        poly_geom=element,
        wkt=wkt,
    )


def write_column_footprint(
    conn: Connection | Session, col_id: int, geometry: ColumnGeometry
) -> bool:
    """Write a column's geometry to its `cols` row, and its polygon to `col_areas`.

    `col_areas` is where the v2 API reads a column's polygon; its rows are replaced, so a
    column without a polygon is left with none. `cols.coordinate` and `cols.wkt` are the
    point, set from `lat`/`lng` by the table's trigger. False when there is no such column.
    """
    params = {
        "col_id": col_id,
        "lat": geometry.lat,
        "lng": geometry.lng,
        "area_km2": geometry.area_km2,
        "wkt": geometry.wkt,
    }
    updated = conn.execute(
        text(
            """
            UPDATE macrostrat.cols SET
              lat = CAST(:lat AS float),
              lng = CAST(:lng AS float),
              col_area = CAST(:area_km2 AS float),
              poly_geom = ST_GeomFromText(CAST(:wkt AS text), 4326)
            WHERE id = :col_id
            """
        ),
        params,
    )
    if updated.rowcount == 0:
        return False

    conn.execute(
        text("DELETE FROM macrostrat.col_areas WHERE col_id = :col_id"), params
    )
    if geometry.wkt is not None:
        conn.execute(
            text(
                """
                INSERT INTO macrostrat.col_areas (col_id, gmap, col_area, wkt)
                VALUES (
                  :col_id, '', ST_GeomFromText(CAST(:wkt AS text), 4326),
                  CAST(:wkt AS text)
                )
                """
            ),
            params,
        )
    return True
