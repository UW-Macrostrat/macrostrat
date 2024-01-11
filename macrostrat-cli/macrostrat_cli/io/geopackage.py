"""
Write a Macrostrat database to a GeoPackage file using the GeoPandas library.

Currently, this represents the Macrostrat internal PostGIS schema more or less unmodified.
As a next step, we will rework it to fit the CriticalMAAS TA1 output schema.
https://github.com/DARPA-CRITICALMAAS/schemas/tree/main/ta1
"""

from macrostrat.database import Database
from macrostrat.database.mapper import BaseModel
from pathlib import Path
from rich import print
from criticalmaas.ta1_geopackage import GeopackageDatabase
from shapely.geometry import mapping
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from pydantic import BaseModel
from typing import Generator
from psycopg2.sql import Identifier


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a Macrostrat map dataset (stored in PostGIS) to a GeoPackage file using GeoPandas and SQLAlchemy."""

    _map = get_map_identifier(db, identifier)

    if filename is None:
        filename = Path(f"{_map.slug}.gpkg")
    _unlink_if_exists(filename, overwrite=overwrite)

    print(f"Map [bold cyan]{_map.slug}[/] (#{_map.id}) -> {filename}")

    # Create the GeoPackage
    gpd = GeopackageDatabaseExt(filename)

    # Get models automapped from the Geopackage schema
    gpd.automap()
    Map = gpd.model.map
    MapMetadata = gpd.model.map_metadata
    LineType = gpd.model.line_type
    PolygonType = gpd.model.polygon_type
    GeologicUnit = gpd.model.geologic_unit
    PointType = gpd.model.point_type

    ### MAP metadata ###

    gpd.write_models(_build_map_metadata(db, _map, Map, MapMetadata))

    ### LINE FEATURES ###

    # Insert the line types
    valid_types = gpd.enum_values("line_type")
    gpd.write_models(_build_line_types(db, _map, LineType, valid_types))
    gpd.write_features("line_feature", _build_line_features(db, _map))

    ### POINT FEATURES ###
    valid_types = gpd.enum_values("point_type")
    gpd.write_models(_build_point_types(db, _map, PointType, valid_types))
    gpd.write_features("point_feature", _build_point_features(db, _map))

    ### POLYGON FEATURES ###

    gpd.write_models(_build_polygon_types(db, _map, PolygonType, GeologicUnit))
    gpd.write_features("polygon_feature", _build_polygon_features(db, _map))


# Helper classes


class GeopackageDatabaseExt(GeopackageDatabase):
    def write_models(self, models: list):
        self.session.add_all(models)
        self.session.commit()

    def enum_values(self, enum_name: str):
        """Get the values of an enum type."""
        table_name = "enum_" + enum_name
        try:
            model = getattr(self.model, table_name)
        except AttributeError:
            raise ValueError(f"Enum type {enum_name} does not exist")

        query = self.session.query(model.name)
        # Insert the line types
        return set(query.all())


class MapIdentifier(BaseModel):
    """A Macrostrat map identifier."""

    id: int
    slug: str
    url: str = None
    name: str = None


# HELPER METHODS FOR SPECIFIC STEPS


def _build_map_metadata(
    db, _map: MapIdentifier, Map: BaseModel, MapMetadata: BaseModel
):
    yield Map(
        id=_map.slug,
        name=_map.name,
        source_url=_map.url,
        image_url="not applicable",
        image_width=-1,
        image_height=-1,
    )

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
        raise_errors=True,
    )

    row = next(res).first()

    yield MapMetadata(
        **row._asdict(),
        provenance="human verified",
        confidence=None,
    )


def _build_point_types(
    db: Database, _map: MapIdentifier, PointType: BaseModel, valid_types: set[str]
):
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
        yield PointType(name=type_name, id=row.type)


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


def _build_line_types(
    db: Database, _map: MapIdentifier, LineType: BaseModel, valid_types: set[str]
):
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
        yield LineType(name=type_name, id=row.type)


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
    db: Database, _map: MapIdentifier, PolygonType: BaseModel, GeologicUnit: BaseModel
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
        unit = GeologicUnit(
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

        ptype = PolygonType(
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
        raise_errors=True,
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


### HELPER METHODS ###


def get_map_identifier(db, identifier: str | int) -> MapIdentifier:
    """Get a map identifier from a map ID or slug."""
    query = "SELECT source_id, slug, name, url FROM maps.sources"
    params = {}
    try:
        map_id = int(identifier)
        query += " WHERE id = %(source_id)s"
        params["source_id"] = map_id
    except ValueError:
        map_slug = identifier
        query += " WHERE slug = %(slug)s"
        params["slug"] = map_slug

    res = next(db.run_sql(query, params=params)).first()

    return MapIdentifier(id=res.source_id, slug=res.slug, url=res.url, name=res.name)


def _unlink_if_exists(filename: Path, overwrite: bool = False):
    file_exists = filename.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        filename.unlink()
