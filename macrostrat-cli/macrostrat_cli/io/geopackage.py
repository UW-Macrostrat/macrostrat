"""
Write a Macrostrat database to a GeoPackage file using the GeoPandas library.

Currently, this represents the Macrostrat internal PostGIS schema more or less unmodified.
As a next step, we will rework it to fit the CriticalMAAS TA1 output schema.
https://github.com/DARPA-CRITICALMAAS/schemas/tree/main/ta1
"""

from macrostrat.database import Database
from geopandas import GeoDataFrame
from pathlib import Path
from rich import print
from criticalmaas.ta1_geopackage import create_geopackage, enable_foreign_keys
from shapely.geometry import mapping
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
import fiona


def write_map_geopackage(
    db: Database, identifier: str | int, filename: str = None, overwrite: bool = False
):
    """Write a Macrostrat map dataset (stored in PostGIS) to a GeoPackage file using GeoPandas and SQLAlchemy."""

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

    if filename is None:
        filename = f"{map_slug}.gpkg"

    print(f"Map [bold cyan]{map_slug}[/] (#{map_id}) -> {filename}")

    fn = Path(filename)
    file_exists = fn.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        fn.unlink()

    params = {"source_id": map_id}

    # Create the GeoPackage
    gpkg = create_geopackage(filename)
    # Insert the map data
    gpd = Database(gpkg.url)
    enable_foreign_keys(gpd.engine)

    # Automap the database schema
    gpd.automap()

    sources_query = """
    SELECT
    slug,
    name,
    url
    FROM maps.sources
    WHERE source_id = %(source_id)s
    """

    res = next(db.run_sql(sources_query, params=params)).first()
    map_id = res.slug

    # Create a model for the map
    Map = gpd.model.map(
        id=map_id,
        name=res.name,
        source_url=res.url,
        image_url="not applicable",
        image_width=-1,
        image_height=-1,
    )
    gpd.session.add(Map)

    gpd.session.commit()

    ### LINE FEATURES ###

    # Insert the line types
    valid_types = set(
        [v[0] for v in next(gpd.run_sql("SELECT name FROM enum_line_type"))]
    )

    # Get all the line types
    res = db.run_sql(
        """
        SELECT DISTINCT type FROM maps.lines WHERE source_id = %(source_id)s;
        """,
        params=params,
    )

    for row in next(res):
        type_name = row.type
        if row.type not in valid_types:
            type_name = "unknown"
        gpd.session.add(gpd.model.line_type(name=type_name, id=row.type))
    gpd.session.commit()

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
        params=params,
    )

    features = []
    for row in next(res):
        vals = dict(
            **row._asdict(),
            polarity="unknown",
            map_id=map_id,
            provenance=None,
            confidence=None,
        )
        geometry = mapping(to_shape(WKBElement(vals.pop("map_geom"))))
        features.append({"geometry": geometry, "properties": vals})

    # Geospatial layers must be opened with Fiona
    with fiona.open(
        filename,
        "a",
        driver="GPKG",
        layer="line_feature",
        crs="EPSG:4326",
        PRELUDE_STATEMENTS="PRAGMA foreign_keys = ON",
    ) as lines:
        lines.writerecords(features)

    ### POINT FEATURES ###
    valid_types = set(
        [v[0] for v in next(gpd.run_sql("SELECT name FROM enum_point_type"))]
    )

    # Get all the point types
    res = db.run_sql(
        """
        SELECT DISTINCT point_type type FROM maps.points WHERE source_id = %(source_id)s;
        """,
        params=params,
    )

    for row in next(res):
        type_name = row.type
        if row.type not in valid_types:
            type_name = "unknown"
        gpd.session.add(gpd.model.point_type(name=type_name, id=row.type))
    gpd.session.commit()

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
        params=params,
    )
    features = []
    for row in next(res):
        vals = dict(**row._asdict(), map_id=map_id, provenance=None, confidence=None)
        geometry = mapping(to_shape(WKBElement(vals.pop("geom"))))
        features.append({"geometry": geometry, "properties": vals})

    with fiona.open(
        filename,
        "a",
        driver="GPKG",
        layer="point_feature",
        crs="EPSG:4326",
        PRELUDE_STATEMENTS="PRAGMA foreign_keys = ON",
    ) as points:
        points.writerecords(features)

    ### POLYGON FEATURES ###

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
        params=params,
    )

    for row in next(res):
        unit = db.model.geologic_unit(
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
        gpd.session.add(unit)

        ptype = db.model.polygon_type(
            id=str(row.legend_id),
            name=row.type,
            color=row.color,
            map_unit=str(row.legend_id),
        )
        gpd.session.add(ptype)

    gpd.session.commit()

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
        params=params,
    )
    features = []
    for row in next(res):
        vals = dict(**row._asdict(), map_id=map_id, provenance=None, confidence=None)
        geometry = mapping(to_shape(WKBElement(vals.pop("geom"))))
        features.append({"geometry": geometry, "properties": vals})

    with fiona.open(
        filename,
        "a",
        driver="GPKG",
        layer="polygon_feature",
        crs="EPSG:4326",
        PRELUDE_STATEMENTS="PRAGMA foreign_keys = ON",
    ) as polygons:
        polygons.writerecords(features)


def get_scalar(db: Database, query: str, params: dict = None):
    """Return a scalar value from a SQL query."""
    return list(db.run_sql(query, params=params))[0].scalar()
