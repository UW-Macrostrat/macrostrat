import time
from os import environ
from pathlib import Path
from subprocess import run

from macrostrat.database import run_sql
from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory
from rich import print
from typer import Typer

from macrostrat.core import MacrostratSubsystem
from ...database._legacy import get_db
from ...database.utils import engine_for_db_name

__dir__ = Path(__file__).parent


class MapsTopologySubsystem(MacrostratSubsystem):
    """Placeholder for when this becomes a bit more formalized..."""

    name = "maps"


cli = Typer(no_args_is_help=True)

config = dict(
    data_schema="map_bounds",
    topo_schema="map_bounds_topology",
    srid=4326,
    tolerance=0.0001,
)


proc = lambda name: __dir__ / "procedures" / f"{name}.sql"


@cli.command("create")
def create_fixtures(reset: bool = False, fill: bool = False):
    """Create topology fixtures"""
    db = get_db()

    if reset:
        drop()

    db.run_fixtures(proc("create-tables"))
    db.run_fixtures(proc("fill-tables"))


@cli.command("drop")
def drop():
    """Drop topology fixtures"""
    db = get_db()
    db.run_fixtures(proc("drop-tables"))


@cli.command("reset")
def reset():
    """Reset topogeometry creation"""
    db = get_db()
    db.run_fixtures(proc("reset-topology"))


@cli.command("update")
def update():
    """Update topology fixtures"""
    db = get_db()

    # Get a list of maps ordered from large to small

    maps = db.run_query(
        """
        SELECT
            a.source_id,
            slug,
            scale,
            area_km
        FROM map_bounds.map_area a
        JOIN maps.sources s
        USING (source_id)
        ORDER BY area_km DESC
    """
    ).all()

    start_time = time.time()
    for map in maps:
        print(
            f"Processing map [bold green]{map.slug}[/][dim] - #[bold gray]{map.source_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
        )
        process_map(db, map.source_id)
        print()

    end_time = time.time()

    print(f"Total time: {end_time - start_time:.3f} seconds")

    return

    conn = db.engine.connect()
    conn.begin()

    for i, row in enumerate(all_rows):
        start_time = time.time()

        km = row.length / 1000
        print(
            f"Row {i+1} of {total} ({row.id}, {row.source_id}, {row.slug}, {km:.1f} km)...",
            end="",
        )
        # Flush to stdout
        print("\r", end="")

        # Your code block to time
        db.run_sql(
            __dir__ / "procedures" / "update-topology-row.sql",
            dict(id=row.id, **db.instance_params),
        )

        # Record end time
        end_time = time.time()

        # Calculate execution time
        execution_time = end_time - start_time

        # Print or log the execution time
        print(f"...{execution_time:.3f} seconds")

        if i % 10 == 0:
            print("Committing...")
            conn.commit()
            conn.begin()
            # _clean_topology(db)

        conn.commit()

    # update_map_layer(db, 1, "Map boundaries")


# -- Decompose map area geometries into smaller polygons
#
# INSERT INTO map_bounds.map_topo (source_id, geometry)
# SELECT
# source_id,
# ST_Subdivide(ST_MakeValid(ST_SnapToGrid(ST_MakeValid(geometry), 0.0001), 256, 0.0001)
# FROM map_bounds.map_area
# WHERE NOT EXISTS (
#     SELECT 1
# FROM map_bounds.map_topo
# WHERE source_id = map_bounds.map_area.source_id
# )
#


def process_map(db, source_id: int):
    # Insert or update the map topo

    t_start = time.time()
    res = db.run_query(
        """
        WITH existing_count AS (
            SELECT COUNT(*) as n
            FROM map_bounds.map_topo
            WHERE source_id = :source_id
        ), ins AS (
            INSERT INTO map_bounds.map_topo (source_id, geometry)
            SELECT
                source_id,
                ST_Subdivide(ST_MakeValid(ST_SnapToGrid(geometry, 0.0001)), 256, 0.0001)
            FROM map_bounds.map_area
            WHERE source_id = :source_id
              AND (SELECT n FROM existing_count) = 0
            RETURNING id, source_id
        )
        SELECT count(*) as inserted, (SELECT n FROM existing_count) as existing
        FROM ins
        """,
        dict(source_id=source_id),
    ).one()
    db.session.commit()
    elapsed = time.time() - t_start
    total = res.inserted + res.existing
    print(f"Processing {total} [cyan]map_topo[/cyan] features")
    print(f"  inserted: {res.inserted}, existing: {res.existing}")
    print(f"  {elapsed:.3f} seconds")


def update_map_layer(db, id: int, name: str):

    all_rows = db.run_query(
        """SELECT l.id, l.source_id, s.slug, ST_Length(l.geometry::geography) as length
                FROM map_bounds.linework l
        LEFT JOIN maps.sources s
            ON l.source_id = s.source_id
        WHERE topo IS null
          AND map_layer = :id
        ORDER BY ST_Length(l.geometry::geography) DESC
        """,
        dict(id=id),
    ).all()
    print("Updating layer", name)
    db.run_sql("SET session_replication_role = replica;")
    total = len(all_rows)

    conn = db.engine.connect()
    conn.begin()

    for i, row in enumerate(all_rows):
        start_time = time.time()

        km = row.length / 1000
        print(
            f"Row {i+1} of {total} ({row.id}, {row.source_id}, {row.slug}, {km:.1f} km)...",
            end="",
        )
        # Flush to stdout
        print("\r", end="")

        # Your code block to time
        run_sql(
            conn,
            __dir__ / "procedures" / "update-topology-row.sql",
            dict(id=row.id, **db.instance_params),
        )

        # Record end time
        end_time = time.time()

        # Calculate execution time
        execution_time = end_time - start_time

        # Print or log the execution time
        print(f"...{execution_time:.3f} seconds")

        if i % 10 == 0:
            print("Committing...")
            conn.commit()
            conn.begin()
            # _clean_topology(db)

        conn.commit()


@cli.command("test")
def test():
    """Test topology fixtures"""
    from macrostrat.core import app

    db_engine = engine_for_db_name("map_topology_test")
    db_url = raw_database_url(db_engine.url)

    environ["TOPO_TESTING_DATABASE_URL"] = db_url

    srcroot = app.settings.srcroot
    topo_mgr = srcroot / "deps/topology-manager"
    with working_directory(topo_mgr):
        run(["pytest", "-s"])
