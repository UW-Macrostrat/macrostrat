import time

from psycopg.sql import SQL, Identifier

from ..database import get_database, sql_file
from ..utils import MapInfo, table_exists


def create_rgeom(
    source: MapInfo,
    *,
    use_maps_schema: bool = None,
    approach: str = "basic",
    srid: int = 4326,
    buffer: float = 0,
    fill_holes: bool = False,
    fix_antimeridian: bool = True,
):
    """Create a unioned reference geometry for a map source.

    Available approaches:
        - basic: Dissolves all map polygons into a single geometry.
        - legacy: A more complex, ring-based approach
    """
    db = get_database()
    start = time.time()
    # TODO: we should run this in a transaction, but it makes tests fail.
    source_id = source.id

    q = "SELECT primary_table FROM maps.sources WHERE source_id = :source_id"
    row = db.run_query(q, {"source_id": source_id}).first()

    name = row.primary_table

    if use_maps_schema is None:
        # Check if the map polygons exist in the maps schema
        use_maps_schema = False
        if table_exists(db, "polygons", schema="maps"):
            use_maps_schema = (
                db.run_query(
                    "SELECT EXISTS (SELECT map_id FROM maps.polygons WHERE source_id = :source_id)",
                    dict(source_id=source_id),
                ).scalar()
                is True
            )

    table = Identifier("sources", name)
    where = "not coalesce(omit, false)"
    geom_column = Identifier("geometry")

    if use_maps_schema:
        table = Identifier("maps", "polygons")
        where = "source_id = :source_id"
        geom_column = Identifier("geom")
    elif not table_exists(db, name, schema="sources"):
        raise ValueError(f"No table found for {name}")
    else:

        # This is a hack to make sure the geometry is a multipolygon
        # We need to make this more standardized and robust.
        db.run_sql(
            "ALTER TABLE {primary_table} RENAME COLUMN geom TO geometry",
            {"primary_table": table},
        )

        print(f"Validating geometry in sources.{row.primary_table}")
        q = "UPDATE {primary_table} SET geometry = ST_Multi(ST_Buffer(geometry, 0))"
        db.run_sql(q, {"primary_table": table})

    print(f"Creating unioned geometry for {source.slug}...")
    db.run_sql(
        """
       WITH res AS (
           SELECT
               source_id,
               ST_Transform(
                   ST_Union(
                       ST_MakeValid(
                           ST_Transform({geom_column}, :srid)
                       )
                   ),
                   4326
               ) AS geometry
           FROM {primary_table}
           WHERE {where_clause}
           GROUP BY source_id
       )
       UPDATE maps.sources
       SET rgeom = res.geometry
       FROM res
       WHERE sources.source_id = :source_id;
        """,
        dict(
            source_id=source_id,
            geom_column=geom_column,
            where_clause=SQL(where),
            primary_table=table,
            srid=srid,
        ),
    )

    print(f"Creating reference geometry using {approach} approach...")
    # Running in a transaction is needed for locally scoped variables to work
    db.run_sql(
        sql_file("rgeom/" + approach),
        dict(
            source_id=source_id,
            srid=srid,
            buffer_distance=buffer,
            fill_holes=fill_holes,
            fix_antimeridian=fix_antimeridian,
        ),
        raise_errors=True,
        commit=True,
    )

    end = time.time()
    dt = end - start

    print(f"Done in {dt:.2f} s")


def create_webgeom(source: MapInfo, legacy: bool = False):
    """Create a simplified geometry for use on the web"""
    db = get_database()
    sql = "UPDATE maps.sources SET web_geom = ST_Envelope(rgeom) WHERE source_id = :source_id;"
    if legacy:
        # legacy mode for complex maps
        sql = sql_file("set-webgeom")

    db.run_sql(sql, {"source_id": source.id})
