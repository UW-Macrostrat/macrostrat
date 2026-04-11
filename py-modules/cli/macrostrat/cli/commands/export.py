import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from enum import Enum

import fiona
from psycopg.types import none
from psycopg2.extras import RealDictCursor
from shapely import from_wkt, make_valid
from shapely.geometry import mapping
from shapely.wkb import loads
from typer import Option, Argument

from ..database import get_database
from ..database._legacy import pgConnection


@dataclass
class ExportArg:
    source_id: int | None = None
    bbox: str | None = None
    wkt: str | None = None


class MapScale(str, Enum):
    tiny = "tiny"
    small = "small"
    medium = "medium"
    large = "large"


class Layer(str, Enum):
    units = "units"
    lines = "lines"


class ExportFeature(str, Enum):
    lith_hierarchy = "lith-hierarchy"


def export_map(
    filename: Path = Argument(..., help="The Geopackage file to export to"),
    spec: str = Argument(
        ...,
        help="The source_id or bounding box to export, or 'global'",
    ),
    scale: MapScale = Option(
        None,
        "--scale",
        help="Force export at a given scale",
    ),
    layer: Layer = Option(None, "--layer", help="Export a specific layer"),
    features: list[ExportFeature] = Option(
        None, "--with", help="Add optional data to the export"
    ),
    trim: bool = False,
    overwrite: bool = False,
):
    """
    macrostrat export <source_id or bbox>:
        Create a GeoPackage of a given map source or from a bounding box. If a
        source_id is provided, the following data will be dumped:
            + The original polygon data
            + The original line data
            + The homogenized polygon data
            + The homogenized line data
            + The record from maps.sources
        If a bounding box is provided, the following data will be dumped:
            + carto polygon table for appropriate scale
            + carto line table for appropriate scale
            + The necessary records from maps.sources
            + All homogenized polygon scales
            + All homogenized line scales

    Usage:
      macrostrat export <source_id or bbox>
      macrostrat export -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
      --force_scale                     Export the given scale with a bbox
    Examples:
      macrostrat export 123
      macrostrat export -90,43,-90,45
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    pth = Path(filename)
    if pth.is_dir():
        raise ValueError(f"{filename} is a directory. Please provide a valid filename.")
    if pth.suffix != ".gpkg":
        raise ValueError(
            f"{filename} is not a GeoPackage file. Please provide a filename with the .gpkg extension."
        )
    if pth.exists():
        if overwrite:
            pth.unlink()
        else:
            raise ValueError(
                f"File {filename} already exists. Please specify the --overwrite flag if you want to overwrite it."
            )

    if features is not None:
        features = set(features)

    run_exporter(
        pth, extract_spec(spec), trim=trim, scale=scale, features=features, layer=layer
    )


def run_exporter(
    filename: Path,
    arg: ExportArg,
    *,
    trim: bool = False,
    scale: MapScale | None = None,
    features: set[ExportFeature] | None = None,
    layer: Layer | None = None,
):
    conn = pgConnection()

    pg = {
        "connection": conn,
        "cursor": conn.cursor(cursor_factory=RealDictCursor),
        "raw_connection": pgConnection,
    }

    db = get_database()
    filename = str(filename)

    # Only one of these should be defined
    source_id = arg.source_id
    bbox = arg.bbox
    wkt = arg.wkt

    layers = {Layer.units, Layer.lines}
    if layer is not None:
        layers = {layer}

    # source_id mode
    if source_id is not None:
        # Validate source_id
        pg["cursor"].execute(
            """
            SELECT name, scale, primary_table, primary_line_table
            FROM maps.sources
            WHERE source_id = %(source_id)s
            """,
            {"source_id": source_id},
        )
        source_info = pg["cursor"].fetchone()
        if source_info is None:
            print("Source %s was not found or is invalid" % (source_id,))
            sys.exit()

        # Write homogenized units
        select = maps_select % (
            source_info["scale"],
            source_info["scale"],
            source_id,
        )
        write_layer(pg, filename, "units", "MultiPolygon", select, {}, maps_schema)

        # Write homogenized lines
        select = lines_select % (
            source_info["scale"],
            source_id,
        )
        write_layer(
            pg,
            filename,
            "lines",
            "MultiLineString",
            select,
            {},
            lines_schema,
        )

        # Write the metadata
        write_sources(pg, filename, [int(source_id)])

        print(f"Wrote source_id {source_id} to {filename}")
        return

    # bbox mode
    geom = None
    if bbox is not None:
        # Validate vertices
        try:
            xmin, ymin, xmax, ymax = bbox
        except:
            print(
                "Invalid bounding box provided. Please make sure all vertices are numbers"
            )
            sys.exit(1)

        if xmin > xmax or ymin > ymax:
            print(
                "Invalid bounding box. Please make sure it is in the format xmin ymin xmax ymax"
            )
            sys.exit(1)

        geom = "ST_SetSRID(ST_MakeEnvelope(%s, %s, %s, %s), 4326)" % (
            xmin,
            ymin,
            xmax,
            ymax,
        )

    if wkt is not None:
        geom = "ST_GeomFromText('%s', 4326)" % (wkt,)

    if geom is None:
        raise ValueError(
            "No valid geometry provided. Please provide either a bounding box or a WKT geometry."
        )

    # Get appropriate scale if not provided
    if scale is None:
        pg["cursor"].execute(
            f"""
            SELECT ST_Area({geom}::geography)/1000000 as area
            """,
        )
        area = int(pg["cursor"].fetchone()["area"])
        # scale = "large"
        if area < 1_000_000:
            scale = "large"
        elif area < 15000000:
            scale = "medium"
        elif area < 80000000:
            scale = "small"
        else:
            scale = "tiny"

        print(
            "Exporting carto data at scale %s based on area of bounding box: %s sq km"
            % (scale, area)
        )

    geom_field = "c.geom"
    if trim:
        geom_field = "ST_Intersection(c.geom, %s)" % (geom,)

    poly_fields = {
        "map_id": "int",
        "legend_id": "int",
        "source_id": "int",
        "name": "str",
        "strat_name": "str",
        "age": "str",
        "lith": "str",
        "descrip": "str",
        "comments": "str",
        "b_interval": "int",
        "t_interval": "int",
        "best_age_bottom": "str",
        "best_age_top": "str",
        "color": "str",
        "unit_ids": "str",
        "strat_name_ids": "str",
        "concept_ids": "str",
        "lith_ids": "str",
    }

    if Layer.units in layers:
        lith_hierarchy_sql = ""
        if ExportFeature.lith_hierarchy in features:
            lith_hierarchy_sql = "(SELECT array_to_string(array_agg(array_to_string(macrostrat.lithology_hierarchy(l), '>')), ',') FROM macrostrat.liths l WHERE id = any(lith_ids)) AS lith_hierarchy,"
            poly_fields["lith_hierarchy"] = "str"

        # Write carto units
        select = """
            SELECT c.map_id, l.legend_id, l.source_id, name,
            strat_name,
            age,
            lith,
            descrip,
            comments,
            b_interval,
            t_interval,
            best_age_bottom,
            best_age_top,
            color,
            array_to_string(unit_ids, ',') AS unit_ids,
            array_to_string(strat_name_ids, ',') AS strat_name_ids,
            array_to_string(concept_ids, ',') AS concept_ids,
            array_to_string(lith_ids, ',') AS lith_ids,
            %s
            ST_Multi(ST_CollectionExtract(%s, 3)) AS geom
            FROM carto.polygons c
            JOIN maps.map_legend ON map_legend.map_id = c.map_id
            JOIN maps.legend l ON l.legend_id = map_legend.legend_id
            WHERE ST_Intersects(c.geom, %s)
              AND scale = '%s'
        """ % (
            lith_hierarchy_sql,
            geom_field,
            geom,
            scale.value,
        )

        write_layer(pg, filename, "units", "MultiPolygon", select, {}, poly_fields)

    if Layer.lines in layers:
        # Write carto lines
        select = """
            SELECT
                c.line_id,
                ll.source_id,
                ll.name,
                ll.type,
                ll.direction,
                ll.descrip,
                ll.new_type,
                ll.new_direction,
                ST_Multi(ST_CollectionExtract(%s, 2)) AS geom
            FROM carto.lines c
            JOIN (
                SELECT * FROM lines.tiny
                UNION ALL
                SELECT * FROM lines.small
                UNION ALL
                SELECT * FROM lines.medium
                UNION ALL
                SELECT * FROM lines.large
            ) ll ON c.line_id = ll.line_id
            WHERE ST_Intersects(c.geom, %s)
              AND scale = '%s'
        """ % (
            geom_field,
            geom,
            scale.value,
        )

        write_layer(
            pg,
            filename,
            "lines",
            "MultiLineString",
            select,
            {},
            {
                "line_id": "int",
                "source_id": "int",
                "name": "str",
                "type": "str",
                "direction": "str",
                "descrip": "str",
                "new_type": "str",
                "new_direction": "str",
            },
        )

    # Write legend
    connection = sqlite3.connect(filename)
    connection.text_factory = str
    cursor = connection.cursor()

    # Write sources
    cursor.execute(
        """
        CREATE TABLE sources (
            source_id integer PRIMARY KEY AUTOINCREMENT,
            name text,
            url text,
            ref_title text,
            authors text,
            ref_year text,
            ref_source text,
            isbn_doi text,
            scale text,
            license text
        )
        """
    )

    select = """
        SELECT
            source_id,
            name,
            url,
            ref_title,
            authors,
            ref_year,
            ref_source,
            isbn_doi,
            scale,
            license
        FROM maps.sources
        WHERE source_id IN (
            SELECT DISTINCT ll.source_id
            FROM (
                SELECT * FROM lines.tiny
                UNION ALL
                SELECT * FROM lines.small
                UNION ALL
                SELECT * FROM lines.medium
                UNION ALL
                SELECT * FROM lines.large
            ) ll
            WHERE ST_Intersects(ll.geom, %s)
        )
    """ % (
        geom
    )
    pg["cursor"].execute(select)
    for row in pg["cursor"]:
        cursor.execute(
            """
            INSERT INTO sources
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["source_id"],
                row["name"],
                row["url"],
                row["ref_title"],
                row["authors"],
                row["ref_year"],
                row["ref_source"],
                row["isbn_doi"],
                row["scale"],
                row["license"],
            ],
        )

    connection.commit()
    connection.close()

    # Write the metadata


def extract_spec(spec: str) -> ExportArg:
    """Extract the specification. This can be a source_id, bbox, or a WKT geometry"""

    if spec == "global":
        return ExportArg(wkt="POLYGON((-180 -90, -180 90, 180 90, 180 -90, -180 -90))")

    # Try to parse as source_id
    try:
        source_id = int(spec)
        return ExportArg(source_id=source_id)
    except ValueError:
        pass

    # Try to parse as bbox
    try:
        bbox = [float(i) for i in spec.split(",")]
        if len(bbox) == 4:
            return ExportArg(bbox=bbox)
    except ValueError:
        pass

    # Try to parse as WKT
    try:
        print("Trying to parse as WKT geometry...")
        geom = from_wkt(spec)
        print(geom.geom_type, geom.is_valid)
        if geom.geom_type not in ["Polygon", "MultiPolygon"]:
            raise ValueError("Only Polygon and MultiPolygon geometries are supported")
        # Doesn't work for polar caps
        if not geom.is_valid:
            geom = make_valid(geom)
        if not geom.is_valid:
            raise ValueError("Invalid geometry provided", geom)
        return ExportArg(wkt=spec)
    except ValueError:
        pass

    raise ValueError(
        "Invalid specification provided. Please provide either a source_id, a bbox in the format xmin,ymin,xmax,ymax, or a valid WKT geometry."
    )


crs = {"no_defs": True, "ellps": "WGS84", "datum": "WGS84", "proj": "longlat"}
maps_schema = {
    "map_id": "int",
    "orig_id": "int",
    "source_id": "int",
    "name": "str",
    "strat_name": "str",
    "age": "str",
    "lith": "str",
    "descrip": "str",
    "comments": "str",
    "macro_t_int": "str",
    "macro_b_int": "str",
    "best_t_age": "float",
    "best_b_age": "float",
    "color": "str",
}

lines_schema = {
    "line_id": "int",
    "orig_id": "int",
    "source_id": "int",
    "name": "str",
    "type": "str",
    "direction": "str",
    "descrip": "str",
    "new_type": "str",
    "new_direction": "str",
}

maps_select = """
SELECT
    m.map_id,
    m.orig_id,
    m.source_id,
    m.name,
    m.strat_name,
    m.age,
    m.lith,
    m.descrip,
    m.comments,
    ti.interval_name AS macro_t_int,
    tb.interval_name AS macro_b_int,
    l.best_age_top AS best_t_age,
    l.best_age_bottom AS best_b_age,
    l.color,
    m.geom
FROM maps.polygons m
LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id
LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id
JOIN lookup_%s l ON m.map_id = l.map_id
WHERE m.source_id = %s
"""

maps_select_intersect = """
SELECT
    m.map_id,
    m.orig_id,
    m.source_id,
    m.name,
    m.strat_name,
    m.age,
    m.lith,
    m.descrip,
    m.comments,
    ti.interval_name AS macro_t_int,
    tb.interval_name AS macro_b_int,
    l.best_age_top AS best_t_age,
    l.best_age_bottom AS best_b_age,
    l.color,
    ST_CollectionExtract(ST_Intersection(m.geom, %s), 3) AS geom
FROM maps.%s m
LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id
LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id
JOIN lookup_%s l ON m.map_id = l.map_id
WHERE ST_Intersects(geom, %s)
"""

lines_select = """
    SELECT
        line_id,
        orig_id,
        source_id,
        name,
        type,
        direction,
        descrip,
        new_type,
        new_direction,
        geom
    FROM lines.%s
    WHERE source_id = %s
"""


def write_sources(pg, filename, sources):
    connection = sqlite3.connect(filename)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE sources (
            source_id integer PRIMARY KEY AUTOINCREMENT,
            name text,
            url text,
            ref_title text,
            authors text,
            ref_year text,
            ref_source text,
            isbn_doi text,
            scale text,
            license text
        )
    """
    )

    pg["cursor"].execute(
        """
        SELECT
            source_id,
            name,
            url,
            ref_title,
            authors,
            ref_year,
            ref_source,
            isbn_doi,
            scale,
            license AS license
        FROM maps.sources
        WHERE source_id = ANY(%(source_ids)s)
    """,
        {"source_ids": sources},
    )
    for row in pg["cursor"]:
        cursor.execute(
            """
            INSERT INTO sources
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                row["source_id"],
                row["name"],
                row["url"],
                row["ref_title"],
                row["authors"],
                row["ref_year"],
                row["ref_source"],
                row["isbn_doi"],
                row["scale"],
                row["license"],
            ],
        )

    connection.commit()
    connection.close()


def get_table_schema(pg, pg_schema, table):
    # First get the field names in the primary table
    pg["cursor"].execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %(primary_table)s AND table_schema = %(pg_schema)s
    """,
        {"primary_table": table, "pg_schema": pg_schema},
    )
    columns = pg["cursor"].fetchall()

    # Format is { field_name: 'datatype' }
    table_schema = {}
    for col in columns:
        if col["column_name"] != "geom":
            data_type = ""
            if col["data_type"] in ["integer", "bigint", "smallint"]:
                data_type = "int"
            elif col["data_type"] in ["character varying", "text", "char"]:
                data_type = "str"
            elif col["data_type"] == "timestamp with time zone":
                data_type = "datetime"
            elif col["data_type"] == "date":
                data_type = "date"
            elif col["data_type"] == "boolean":
                data_type = "bool"
            elif col["data_type"] in ["double precision", "numeric", "real"]:
                data_type = "float"
            else:
                data_type = "str"

            table_schema[col["column_name"]] = data_type

    # Get a list of column names
    column_names = [col["column_name"] for col in columns]

    select = "SELECT %s FROM %s.%s" % (",".join(column_names), pg_schema, table)

    return table_schema, select


# Given a table, write a layer to a given geopackage
def write_layer(
    pg, filename, layer_name, geometry_type, select, select_params, table_schema
):
    # Open the GeoPackage for writing
    with fiona.open(
        filename,
        "w",
        layer=layer_name,
        driver="GPKG",
        crs=crs,
        schema={"geometry": geometry_type, "properties": table_schema},
    ) as output:
        pg["cursor"].execute(select, select_params)

        for row in pg["cursor"]:
            # Create a shapely geometry from the wkb and dump it into a dict
            geometry = mapping(loads(row["geom"], hex=True))
            del row["geom"]
            # Make sure data types are correct
            for key in row:
                # Postgres often returns these as decimals
                if table_schema[key] == "float" and row[key] is not None:
                    row[key] = float(row[key])
                elif table_schema[key] == "str" and row[key] is not None:
                    row[key] = str(row[key])
            # Write the row to the GeoPackage
            output.write({"geometry": geometry, "properties": row})


def write_original_layers(pg, source_info, filename):
    """Write original units (from sources schema) to the geopackage
    Note: this is currently disabled
    """
    # Write orignal units
    layer_schema, select = get_table_schema(pg, "sources", source_info["primary_table"])
    write_layer(
        pg,
        filename,
        "original_units",
        "MultiPolygon",
        select,
        {},
        layer_schema,
    )

    # Write original lines
    layer_schema, select = get_table_schema(
        pg, "sources", source_info["primary_line_table"]
    )
    write_layer(
        pg,
        filename,
        "original_lines",
        "MultiLineString",
        select,
        {},
        layer_schema,
    )
