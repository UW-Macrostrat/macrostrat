"""
Write a Macrostrat database to a GeoPackage file using the GeoPandas library.

Currently, this represents the Macrostrat internal PostGIS schema more or less unmodified.
As a next step, we will rework it to fit the CriticalMAAS TA1 output schema.
https://github.com/DARPA-CRITICALMAAS/schemas/tree/main/ta1
"""

from macrostrat.database import Database
from pathlib import Path
from rich import print
from criticalmaas.ta1_geopackage import GeopackageDatabase
from shapely.geometry import mapping
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
import fiona
from pydantic import BaseModel
from typing import Generator


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a Macrostrat map dataset (stored in PostGIS) to a GeoPackage file using GeoPandas and SQLAlchemy."""

    _map = get_map_identifier(db, identifier)

    if filename is None:
        filename = f"{_map.slug}.gpkg"

    print(f"Map [bold cyan]{_map.slug}[/] (#{_map.id}) -> {filename}")

    fn = Path(filename)
    file_exists = fn.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        fn.unlink()

    params = {"source_id": _map.id}

    # Create the GeoPackage
    gpd = GeopackageDatabaseExt(filename)

    sources_query = """
    SELECT
    slug,
    name,
    url
    FROM maps.sources
    WHERE source_id = %(source_id)s
    """

    res = next(db.run_sql(sources_query, params=params)).first()

    # Create a model for the map
    Map = gpd.model.map(
        id=_map.slug,
        name=res.name,
        source_url=res.url,
        image_url="not applicable",
        image_width=-1,
        image_height=-1,
    )
    gpd.write_models([Map])

    ### LINE FEATURES ###

    # Insert the line types
    gpd.write_models(_build_line_types(db, _map, gpd))
    gpd.write_features("line_feature", _build_line_features(db, _map))

    ### POINT FEATURES ###

    gpd.write_models(_build_point_types(db, _map, gpd))
    gpd.write_features("point_feature", _build_point_features(db, _map))

    ### POLYGON FEATURES ###

    gpd.write_models(_build_polygon_types(db, _map, gpd))
    gpd.write_features("polygon_feature", _build_polygon_features(db, _map))

    ### MAP metadata ###
    gpd.write_models(_build_map_metadata(db, _map, gpd))


class GeopackageDatabaseExt(GeopackageDatabase):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.automap()

    def write_models(self, models: list):
        self.session.add_all(models)
        self.session.commit()


class MapIdentifier(BaseModel):
    """A Macrostrat map identifier."""

    id: int
    slug: str


def get_map_identifier(db, identifier: str | int) -> MapIdentifier:
    """Get a map identifier from a map ID or slug."""
    try:
        map_id = int(identifier)
        map_slug = get_scalar(
            db,
            "SELECT slug FROM maps.sources WHERE source_id = %(source_id)s",
            dict(source_id=map_id),
        )
    except ValueError:
        map_slug = identifier
        map_id = get_scalar(
            db,
            "SELECT source_id FROM maps.sources WHERE slug = %(slug)s",
            params=dict(slug=map_slug),
        )
    return MapIdentifier(id=map_id, slug=map_slug)


def get_scalar(db: Database, query: str, params: dict = None):
    """Return a scalar value from a SQL query."""
    return list(db.run_sql(query, params=params))[0].scalar()


def _build_point_types(db: Database, _map: MapIdentifier, gpd: GeopackageDatabaseExt):
    valid_types = set(
        [v[0] for v in next(gpd.run_sql("SELECT name FROM enum_point_type"))]
    )

    # Get all the point types
    res = db.run_sql(
        """
        SELECT DISTINCT point_type type FROM maps.points WHERE source_id = %(source_id)s;
        """,
        params={"source_id": _map.id},
    )

    for row in next(res):
        type_name = row.type
        if row.type not in valid_types:
            type_name = "unknown"
        yield gpd.model.point_type(name=type_name, id=row.type)


def _build_point_features(db: Database, _map: MapIdentifier):
    res = db.run_sql(
        """
        SELECT
            point_id id,
            COALESCE(dip_dir, strike+90) dip_direction,
            dip,
            point_type "type",
            geom
        FROM maps.points p
        WHERE p.source_id = %(source_id)s;
        """,
        params=dict(source_id=_map.id),
    )
    for row in next(res):
        vals = dict(
            **row._asdict(),
            map_id=_map.slug,
            provenance="human verified",
            confidence=None,
        )
        geometry = mapping(to_shape(WKBElement(vals.pop("geom"))))
        yield {"geometry": geometry, "properties": vals}


def _build_line_types(db: Database, _map: MapIdentifier, gpd: GeopackageDatabaseExt):
    # Insert the line types
    valid_types = set(
        [v[0] for v in next(gpd.run_sql("SELECT name FROM enum_line_type"))]
    )

    # Get all the line types
    res = db.run_sql(
        """
        SELECT DISTINCT type FROM maps.lines WHERE source_id = %(source_id)s;
        """,
        params={"source_id": _map.id},
    )

    for row in next(res):
        type_name = row.type
        if row.type not in valid_types:
            type_name = "unknown"
        yield gpd.model.line_type(name=type_name, id=row.type)


def _build_line_features(db: Database, _map: MapIdentifier):
    res = db.run_sql(
        """
        SELECT
            line_id::TEXT id,
            geom map_geom,
            l.name,
            l.type
        FROM maps.lines l
        WHERE l.source_id = %(source_id)s;
        """,
        params=dict(source_id=_map.id),
    )

    for row in next(res):
        vals = dict(
            **row._asdict(),
            polarity="unknown",
            map_id=_map.slug,
            provenance="human verified",
            confidence=None,
        )
        geometry = mapping(to_shape(WKBElement(vals.pop("map_geom"))))
        yield {"geometry": geometry, "properties": vals}


def _build_polygon_types(
    db: Database, _map: MapIdentifier, gpd: GeopackageDatabaseExt
) -> Generator[object, None, None]:
    res = db.run_sql(
        """
        SELECT DISTINCT ON (l.legend_id)
            p.name,
            l.legend_id,
            CASE WHEN p.name = 'water' THEN 'body of water' ELSE 'geologic unit' END "type",
            color,
            l.descrip description,
            l.age age_text,
            t_int.interval_name t_interval,
            b_int.interval_name b_interval,
            best_age_top t_age,
            best_age_bottom b_age,
            (SELECT string_agg(DISTINCT li.lith, ', ')
            FROM maps.legend_liths ll
            JOIN macrostrat.liths li
                ON li.id = ll.lith_id
                WHERE ll.legend_id = l.legend_id
            ) AS lithology
        FROM maps.polygons p
        LEFT JOIN maps.map_legend ml
        ON p.map_id = ml.map_id
        LEFT JOIN maps.legend l
        ON l.legend_id = ml.legend_id
        LEFT JOIN macrostrat.intervals t_int
        ON t_int.id = l.t_interval
        LEFT JOIN macrostrat.intervals b_int
        ON b_int.id = l.b_interval
        WHERE p.source_id = %(source_id)s;
        """,
        params=dict(source_id=_map.id),
    )

    for row in next(res):
        unit = gpd.model.geologic_unit(
            id=str(row.legend_id),
        )
        for field in [
            "name",
            "description",
            "age_text",
            "t_interval",
            "b_interval",
            "t_age",
            "b_age",
            "lithology",
        ]:
            setattr(unit, field, getattr(row, field))
        yield unit

        ptype = gpd.model.polygon_type(
            id=str(row.legend_id),
            name=row.type,
            color=row.color,
            map_unit=str(row.legend_id),
        )
        yield ptype


def _build_polygon_features(db, _map: MapIdentifier):
    res = db.run_sql(
        """
        SELECT DISTINCT ON (p.map_id)
            p.map_id::text id,
            p.geom,
            ml.legend_id::text "type"
        FROM maps.polygons p
        JOIN maps.map_legend ml
          ON p.map_id = ml.map_id
        WHERE p.source_id = %(source_id)s;
        """,
        params=dict(source_id=_map.id),
    )
    for row in next(res):
        vals = dict(
            **row._asdict(),
            map_id=_map.slug,
            provenance="human verified",
            confidence=None,
        )
        geometry = mapping(to_shape(WKBElement(vals.pop("geom"))))
        yield {"geometry": geometry, "properties": vals}


def _build_map_metadata(db, _map: MapIdentifier, gpd: GeopackageDatabaseExt):
    res = db.run_sql(
        """
        SELECT
            slug id,
            slug map_id,
            ref_title title,
            authors,
            ref_source publisher,
            ref_year "year"
        FROM maps.sources WHERE source_id = %(source_id)s
        """,
        params={"source_id": _map.id},
    )

    for row in next(res):
        vals = dict(
            **row._asdict(),
            provenance="human verified",
            confidence=None,
        )
        yield gpd.model.map_metadata(**vals)
