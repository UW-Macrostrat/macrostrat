from typing import Generator

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from macrostrat.database import Database
from macrostrat.database.mapper import BaseModel
from macrostrat.map_integration import MapInfo
from shapely.geometry import mapping


def _build_map_metadata(db, _map: MapInfo, Map: BaseModel, MapMetadata: BaseModel):
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
    db: Database, _map: MapInfo, PointType: BaseModel, valid_types: set[str]
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


def _build_point_features(db: Database, _map: MapInfo):
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
    db: Database, _map: MapInfo, LineType: BaseModel, valid_types: set[str]
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


def _build_line_features(db: Database, _map: MapInfo):
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
    db: Database, _map: MapInfo, PolygonType: BaseModel, GeologicUnit: BaseModel
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


def _build_polygon_features(db, _map: MapInfo):
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
