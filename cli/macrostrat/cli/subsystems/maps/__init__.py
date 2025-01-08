import time
from os import environ
from pathlib import Path
from subprocess import run

from macrostrat.database import run_sql
from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory
from typer import Typer

from macrostrat.core import MacrostratSubsystem
from mapboard.topology_manager import create_tables, drop_tables
from mapboard.topology_manager.database import _get_instance_params
from mapboard.topology_manager.utilities import enable_triggers
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


@cli.command("create")
def create_fixtures(reset: bool = False, fill: bool = False):
    """Create topology fixtures"""
    db = get_db()

    if reset:
        drop_tables(db, **config)

    create_tables(db, **config)

    if fill:
        db.run_sql(__dir__ / "procedures" / "fill-topology.sql")

    db.run_fixtures(__dir__ / "fixtures")


@cli.command("drop")
def drop():
    """Drop topology fixtures"""
    db = get_db()
    drop_tables(db, **config)


@cli.command("fill")
def fill():
    """Fill topology fixtures"""
    db = get_db()

    db.run_sql(__dir__ / "procedures" / "fill-topology.sql")


@cli.command("update")
def update():
    """Update topology fixtures"""
    db = get_db()
    db.instance_params = _get_instance_params(**config)
    # _update(db, bulk=True)

    update_map_layer(db, 2, "Grid")
    update_map_layer(db, 1, "Map boundaries")

    enable_triggers(db, False)


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
